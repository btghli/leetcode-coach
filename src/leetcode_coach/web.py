"""Local learning workbench; LangGraph remains the conversation owner."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import queue
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from langchain.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from .config import load_config
from .engines import build_decision_engine
from .graph import TrainingGraph
from .message_content import normalize_message_content
from .services import StudyService, PatternSweepService, MetadataResolver, find_root
from .streaming import event_sink


class Workbench:
    def __init__(self, root, graph):
        self.study = StudyService(root)
        self.sweep = PatternSweepService(root)
        self.graph = graph
        self.lock = asyncio.Lock()

    def overview(self):
        categories = self.sweep.status()['categories']
        for category in categories:
            card = self.sweep.pattern_card(category['slug'])
            category['content'] = card['content'] if card else '模板待补充'
        sessions = []
        for path in sorted((self.study.root / 'study/sessions').glob('*.md'), reverse=True)[:10]:
            sessions.append({'date': path.stem, 'content': path.read_text(encoding='utf-8')})
        return {'status': self.study.status(), 'plan': self.study.plan_day(),
                'categories': categories, 'sessions': sessions}

    async def conversation(self, thread, payload=None, sink=None):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', thread):
            raise ValueError('无效会话编号')
        config = {'configurable': {'thread_id': thread}}
        async with self.lock:
            if payload is not None:
                action = payload.get('action')
                snapshot = await self.graph.aget_state(config)
                if action in ('approve', 'reject'):
                    if not snapshot.values.get('pending_action') or not any(t.interrupts for t in snapshot.tasks):
                        raise ValueError('当前没有待审批操作，请刷新会话')
                    value = Command(resume={'type': action})
                elif action == 'start':
                    value = {'messages': []}
                elif action == 'message':
                    message = payload.get('message', '')
                    if not isinstance(message, str) or not message.strip() or len(message) > 50000:
                        raise ValueError('请输入 1–50000 字符的消息')
                    value = {'messages': [HumanMessage(content=message)]}
                else:
                    raise ValueError('不支持的操作')
                if sink is None:
                    await self.graph.ainvoke(value, config=config)
                else:
                    token = event_sink.set(sink)
                    try:
                        async for update in self.graph.astream(value, config=config, stream_mode='updates'):
                            for node in update:
                                if not node.startswith('__'):
                                    sink({'type': 'stage', 'node': node})
                    finally:
                        event_sink.reset(token)
            snapshot = await self.graph.aget_state(config)
            state = snapshot.values
            return {
                'thread': thread,
                'messages': [{'role': m.type, 'content': normalize_message_content(m.content)}
                             for m in state.get('messages', []) if m.type in ('ai', 'human')],
                **{key: state.get(key) for key in ('phase', 'selected_problem', 'pending_action',
                   'teach_back_assessment', 'judge_result', 'attempt_recorded', 'last_error')},
                # Presentation-only data is recomputed from the authoritative
                # repository instead of being checkpointed in conversation state.
                'day_plan': self.study.plan_day(),
            }

    async def threads(self):
        result = {}
        async with self.lock:
            async for checkpoint in self.graph.checkpointer.alist(None):
                thread = checkpoint.config['configurable']['thread_id']
                if thread not in result:
                    values = checkpoint.checkpoint.get('channel_values', {})
                    result[thread] = {'id': thread, 'title': (values.get('selected_problem') or {}).get('title', '学习会话')}
        return list(result.values())

    async def read(self, slug=None):
        # Do not expose partially committed data while a graph turn is saving.
        async with self.lock:
            return self.overview() if slug is None else self.study.problem_context(slug)


def handler_for(workbench, loop):
    assets = Path(__file__).parent / 'static'

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def stream_conversation(self, thread, payload):
            events = queue.Queue()
            disconnected = threading.Event()
            def publish(event):
                if not disconnected.is_set():
                    events.put(event)
            async def produce():
                try:
                    result = await workbench.conversation(thread, payload, publish)
                    publish({'type': 'done', 'conversation': result})
                except ValueError as exc:
                    publish({'type': 'error', 'message': str(exc)})
                except Exception:
                    logging.exception('Streaming conversation failed')
                    publish({'type': 'error', 'message': '回复失败，请刷新会话确认状态后重试。'})
            asyncio.run_coroutine_threadsafe(produce(), loop)
            self.send_response(200)
            self.send_header('Content-Type', 'application/x-ndjson; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.close_connection = True
            try:
                while True:
                    try:
                        event = events.get(timeout=5)
                    except queue.Empty:
                        event = {'type': 'heartbeat'}
                    self.wfile.write((json.dumps(event, ensure_ascii=True) + '\n').encode())
                    self.wfile.flush()
                    if event['type'] in ('done', 'error'):
                        break
            except (BrokenPipeError, ConnectionResetError):
                # Finish/checkpoint the in-flight graph turn, never retry a write automatically.
                pass
            finally:
                disconnected.set()

        def send(self, status, body, content_type='application/json; charset=utf-8'):
            data = json.dumps(body, ensure_ascii=False).encode() if content_type.startswith('application/json') else body
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def dispatch(self, payload=None):
            expected = f'127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host') != expected or self.headers.get('Origin', f'http://{expected}') != f'http://{expected}':
                self.send(403, {'error': '仅允许本地同源访问'})
                return
            parsed = urlsplit(self.path)
            params = parse_qs(parsed.query)
            try:
                if parsed.path == '/api/conversation/stream' and payload is not None:
                    self.stream_conversation(params.get('thread', ['workbench'])[0], payload)
                elif parsed.path == '/api/threads' and payload is None:
                    self.send(200, asyncio.run_coroutine_threadsafe(workbench.threads(), loop).result())
                elif parsed.path == '/api/conversation':
                    result = asyncio.run_coroutine_threadsafe(
                        workbench.conversation(params.get('thread', ['workbench'])[0], payload), loop
                    ).result()
                    self.send(200, result)
                elif payload is not None:
                    self.send(404, {'error': '接口不存在'})
                elif parsed.path == '/api/overview':
                    self.send(200, asyncio.run_coroutine_threadsafe(workbench.read(), loop).result())
                elif parsed.path == '/api/note':
                    result = asyncio.run_coroutine_threadsafe(
                        workbench.read(params.get('slug', [''])[0]), loop
                    ).result()
                    self.send(200 if result else 404, result or {'error': '这道题尚无本地笔记'})
                elif parsed.path in ('/', '/app.js', '/style.css'):
                    name = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}[parsed.path]
                    mime = {'/': 'text/html', '/app.js': 'text/javascript', '/style.css': 'text/css'}[parsed.path]
                    self.send(200, (assets / name).read_bytes(), mime + '; charset=utf-8')
                else:
                    self.send(404, {'error': '页面不存在'})
            except ValueError as exc:
                self.send(400, {'error': str(exc)})
            except Exception:
                logging.exception('Workbench request failed')
                self.send(500, {'error': '操作失败。请刷新会话查看状态后重试；检查终端配置与模型连接。'})

        def do_GET(self):
            self.dispatch()

        def do_POST(self):
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 200000 or self.headers.get('Content-Type') != 'application/json':
                    raise ValueError()
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError()
            except (ValueError, json.JSONDecodeError):
                self.send(400, {'error': '无效请求'})
                return
            self.dispatch(payload)

    return Handler


async def serve(root, port=2025, open_browser=True):
    config = load_config(root)
    config.resolved_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    study, sweep = StudyService(root), PatternSweepService(root)
    async with AsyncSqliteSaver.from_conn_string(str(config.resolved_checkpoint_path)) as saver:
        graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep, config.mcp),
                              build_decision_engine(config, study, sweep)).build(saver)
        server = ThreadingHTTPServer(('127.0.0.1', port), handler_for(Workbench(root, graph), asyncio.get_running_loop()))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}'
        print(f'LeetCode Coach: {url}', flush=True)
        if open_browser:
            webbrowser.open(url)
        try:
            await asyncio.Event().wait()
        finally:
            server.shutdown()
            server.server_close()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=2025)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    try:
        asyncio.run(serve(find_root(), args.port, not args.no_browser))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
