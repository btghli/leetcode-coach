import io
import json
import subprocess
import threading
from unittest.mock import Mock

import pytest

from leetcode_coach.codex_stream import (
    ResponsePreview, run_codex_stream, CodexStreamError, _isolated_codex_environment,
)
from leetcode_coach.streaming import event_sink, emit


@pytest.fixture
def workbench(study_repo):
    from langgraph.checkpoint.memory import InMemorySaver
    from leetcode_coach.graph import TrainingGraph
    from leetcode_coach.schemas import ProblemMetadata
    from leetcode_coach.services import StudyService, PatternSweepService, MetadataResolver
    from leetcode_coach.web import Workbench
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug='two-sum', title='Two Sum', difficulty='Easy', lists=['example']))
    engine = Mock()
    graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep), engine).build(InMemorySaver())
    result = Workbench(study_repo, graph)
    result.test_engine = engine
    return result


def test_preview_exposes_only_response_and_handles_split_escapes():
    events = []
    token = event_sink.set(events.append)
    try:
        preview = ResponsePreview()
        raw = json.dumps({'action': 'hint', 'response': '中文\n"quoted" 😀', 'requested_mode': None})
        for c in raw:
            preview.append(c)
        assert events[-1]['text'] == '中文\n"quoted" 😀'
        assert len(events) > 2
        assert all('action' not in e['text'] for e in events)
    finally:
        event_sink.reset(token)


def test_isolated_codex_environment_copies_only_login_file(tmp_path, monkeypatch):
    source_home = tmp_path / 'source-codex-home'
    source_home.mkdir()
    (source_home / 'auth.json').write_text('{"tokens": {}}', encoding='utf-8')
    monkeypatch.setenv('CODEX_HOME', str(source_home))

    isolated = _isolated_codex_environment(tmp_path)
    try:
        assert isolated is not None
        assert (isolated / 'auth.json').read_text(encoding='utf-8') == '{"tokens": {}}'
        assert (isolated / 'config.toml').read_text(encoding='utf-8') == '[mcp_servers]\n'
        assert (isolated / 'auth.json').stat().st_mode & 0o777 == 0o600
        assert isolated.stat().st_mode & 0o777 == 0o700
    finally:
        if isolated:
            import shutil
            shutil.rmtree(isolated)


def fake_process(events):
    return Mock(stdin=io.StringIO(), stdout=io.StringIO(''.join(json.dumps(e)+'\n' for e in events)),
                poll=Mock(return_value=None))


def handshake():
    return [{'id': 1, 'result': {}}, {'id': 2, 'result': {'thread': {'id': 't'}}}]


def test_app_server_emits_preview_before_completion_and_cleans_up(tmp_path):
    events = []
    answer = json.dumps({'action': 'hint', 'response': 'hello world'})
    process = fake_process(handshake() + [
        {'method': 'item/agentMessage/delta', 'params': {'threadId': 't', 'itemId': 'a', 'delta': answer[:40]}},
        {'method': 'item/agentMessage/delta', 'params': {'threadId': 't', 'itemId': 'a', 'delta': answer[40:]}},
        {'method': 'item/completed', 'params': {'item': {'type': 'agentMessage', 'text': answer}}},
        {'method': 'thread/tokenUsage/updated', 'params': {'tokenUsage': {'total': {'inputTokens': 10, 'outputTokens': 5}}}},
        {'method': 'turn/completed', 'params': {'turn': {'status': 'completed'}}},
    ])
    captured = {}
    def popen(*args, **kwargs):
        captured['command'] = args[0]
        return process
    token = event_sink.set(events.append)
    try:
        result, usage = run_codex_stream('codex', 'prompt', {}, tmp_path, None, 1, popen=popen)
    finally:
        event_sink.reset(token)
    assert result == answer and usage['total_tokens'] == 15
    assert [e['text'] for e in events if e['type'] == 'preview'][-1] == 'hello world'
    process.terminate.assert_called_once()
    assert process.stdin.closed and process.stdout.closed
    assert not any('enabled=false' in item for item in captured['command'])
    assert not any(item.startswith('mcp_servers=') for item in captured['command'])


@pytest.mark.parametrize('tail', [
    [],  # EOF before completion
    [{'id': 3, 'error': {'message': 'invalid'}}],
    [{'method': 'turn/completed', 'params': {'turn': {'status': 'failed'}}}],
    [{'method': 'item/commandExecution/requestApproval', 'id': 10, 'params': {}}],
])
def test_app_server_failures_never_return_partial_decisions(tmp_path, tail):
    process = fake_process(handshake()+tail)
    with pytest.raises(CodexStreamError):
        run_codex_stream('codex', 'prompt', {}, tmp_path, None, 1, popen=lambda *a, **kw: process)
    process.terminate.assert_called_once()


def test_app_server_timeout_cleans_up(tmp_path):
    process = fake_process([])
    with pytest.raises(subprocess.TimeoutExpired):
        run_codex_stream('codex', 'prompt', {}, tmp_path, None, -1, popen=lambda *a, **kw: process)
    process.terminate.assert_called_once()


async def test_http_stream_delivers_preview_before_engine_finishes(workbench):
    import asyncio
    from http.client import HTTPConnection
    from http.server import ThreadingHTTPServer
    from leetcode_coach.web import handler_for
    from leetcode_coach.schemas import TurnDecision

    await workbench.conversation('stream-test', {'action': 'start'})
    release = threading.Event()
    def decide(state):
        emit('preview', id='p', text='第一段')
        assert release.wait(5)
        emit('preview', id='p', text='第一段，第二段')
        return TurnDecision(action='hint', response='第一段，第二段')
    workbench.test_engine.decide = decide
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(workbench, asyncio.get_running_loop()))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    def request():
        client = HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        try:
            client.request('POST', '/api/conversation/stream?thread=stream-test',
                           json.dumps({'action': 'message', 'message': '提示'}), {'Content-Type': 'application/json'})
            response = client.getresponse()
            assert response.status == 200
            assert response.getheader('Content-Type').startswith('application/x-ndjson')
            first = json.loads(response.readline())
            assert first == {'type': 'preview', 'id': 'p', 'text': '第一段'}
            assert not release.is_set()  # proves the response isn't buffered until completion
            release.set()
            rest = [json.loads(line) for line in response.read().splitlines()]
            assert rest[-1]['type'] == 'done'
            assert rest[-1]['conversation']['messages'][-1]['content'] == '第一段，第二段'
        finally:
            release.set()
            client.close()
    try:
        await asyncio.to_thread(request)
    finally:
        release.set()
        await asyncio.to_thread(server.shutdown)
        server.server_close()
        worker.join()
