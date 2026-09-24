"""Single ephemeral Codex app-server turn over stdio using existing CLI auth."""
import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path

from pydantic_core import from_json

from .streaming import emit


class CodexStreamError(RuntimeError):
    pass


class ResponsePreview:
    def __init__(self):
        self.id = uuid.uuid4().hex
        self.raw = ''
        self.text = ''

    def append(self, delta):
        self.raw += delta
        try:
            value = from_json(self.raw, allow_partial='trailing-strings')
        except ValueError:
            return
        text = value.get('response') if isinstance(value, dict) else None
        if isinstance(text, str) and text != self.text:
            self.text = text
            emit('preview', id=self.id, text=text)


def _isolated_codex_environment(workdir):
    """Use local Codex login, without loading user plugins or MCP servers."""
    source_home = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex'))
    source_auth = source_home / 'auth.json'
    if not source_auth.is_file():
        return None
    home = Path(tempfile.mkdtemp(prefix='codex-home-', dir=workdir))
    try:
        os.chmod(home, 0o700)
        target_auth = home / 'auth.json'
        shutil.copyfile(source_auth, target_auth)
        os.chmod(target_auth, 0o600)
        (home / 'config.toml').write_text('[mcp_servers]\n', encoding='utf-8')
        return home
    except Exception:
        shutil.rmtree(home, ignore_errors=True)
        raise


def run_codex_stream(executable, prompt, schema, workdir, model, timeout, popen=subprocess.Popen):
    command = [executable, 'app-server', '--stdio']
    for override in ('web_search="disabled"', 'features.shell_tool=false',
                     'features.code_mode=false', 'features.apply_patch_freeform=false',
                     'features.hooks=false', 'notify=[]', 'project_doc_max_bytes=0'):
        command.extend(['-c', override])
    # stderr is deliberately not forwarded: it can include provider/config details.
    isolated_home = _isolated_codex_environment(workdir) if popen is subprocess.Popen else None
    environment = {**os.environ, 'CODEX_HOME': str(isolated_home)} if isolated_home else None
    process = popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    text=True, encoding='utf-8', bufsize=1, cwd=workdir, env=environment)
    inbox = queue.Queue()
    def reader():
        try:
            for line in process.stdout:
                inbox.put(line)
        finally:
            inbox.put(None)
    worker = threading.Thread(target=reader, daemon=True)
    worker.start()
    deadline = time.monotonic() + timeout
    previews, answer, usage = {}, '', None

    def send(value):
        process.stdin.write(json.dumps(value) + '\n')
        process.stdin.flush()

    def receive():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(command, timeout)
        try:
            line = inbox.get(timeout=remaining)
        except queue.Empty:
            raise subprocess.TimeoutExpired(command, timeout) from None
        if line is None:
            raise CodexStreamError('Codex stream closed before completion')
        try:
            value = json.loads(line)
        except ValueError:
            raise CodexStreamError('Invalid Codex stream event') from None
        if 'method' in value and 'id' in value:
            # A decision engine must never request approval, tools or user input.
            send({'id': value['id'], 'error': {'code': -32601, 'message': 'Tools and approvals disabled'}})
            raise CodexStreamError('Codex requested an operation outside the decision contract')
        return value

    def request(identifier, method, params):
        send({'id': identifier, 'method': method, 'params': params})
        while True:
            event = receive()
            if event.get('id') == identifier:
                if 'error' in event:
                    raise CodexStreamError(f'Codex rejected {method}; check CLI version and configuration')
                return event['result']

    try:
        emit('status', text='正在连接 Codex…')
        request(1, 'initialize', {'clientInfo': {'name': 'leetcode_coach', 'version': '0.2.0'}})
        send({'method': 'initialized', 'params': {}})
        thread = request(2, 'thread/start', {
            'cwd': str(workdir), 'ephemeral': True, 'sandbox': 'read-only', 'approvalPolicy': 'never',
            'model': model, 'modelProvider': 'openai',
            'baseInstructions': 'You are a bounded decision engine. Never use tools. Return only the requested JSON.',
        })['thread']['id']
        # Do not wait separately for the response: deltas may precede its acknowledgement.
        send({'id': 3, 'method': 'turn/start', 'params': {
            'threadId': thread, 'input': [{'type': 'text', 'text': prompt}], 'outputSchema': schema,
            'approvalPolicy': 'never',
            'sandboxPolicy': {'type': 'readOnly'},
        }})
        emit('status', text='Coach 正在生成回复…')
        while True:
            event = receive()
            if event.get('id') == 3 and 'error' in event:
                raise CodexStreamError('Codex rejected turn/start: ' + event['error'].get('message', ''))
            method, params = event.get('method'), event.get('params', {})
            if params.get('threadId', thread) != thread:
                continue
            if method == 'item/agentMessage/delta':
                preview = previews.setdefault(params['itemId'], ResponsePreview())
                preview.append(params['delta'])
            elif method == 'item/completed' and params.get('item', {}).get('type') == 'agentMessage':
                answer = params['item']['text']
            elif method == 'thread/tokenUsage/updated':
                raw = params.get('tokenUsage', {}).get('total', {})
                if all(type(raw.get(k)) is int and raw[k] >= 0 for k in ('inputTokens', 'outputTokens')):
                    usage = {'input_tokens': raw['inputTokens'], 'output_tokens': raw['outputTokens'],
                             'total_tokens': raw['inputTokens'] + raw['outputTokens']}
                    if type(raw.get('cachedInputTokens')) is int:
                        usage['input_token_details'] = {'cache_read': raw['cachedInputTokens']}
            elif method == 'turn/completed':
                if params.get('turn', {}).get('status') != 'completed':
                    raise CodexStreamError('Codex turn failed or was interrupted')
                if not answer:
                    raise CodexStreamError('Codex completed without a final decision')
                return answer, usage
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
        process.stdin.close()
        worker.join(timeout=3)
        process.stdout.close()
        if isolated_home:
            shutil.rmtree(isolated_home, ignore_errors=True)
