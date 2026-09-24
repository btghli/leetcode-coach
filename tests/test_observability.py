import json
import subprocess
import sys
from contextlib import contextmanager
from unittest.mock import Mock

from langchain.messages import HumanMessage
from langsmith import Client

from leetcode_coach.engines import CodexCliDecisionEngine, parse_codex_events
from leetcode_coach.observability import Observer, RedactingClient, get_observer, redact
from leetcode_coach.services import StudyService


def events(answer, usage=None):
    items = [{'type': 'item.completed', 'item': {'type': 'agent_message', 'text': answer}}]
    if usage is not None:
        items.append({'type': 'turn.completed', 'usage': usage})
    return '\n'.join(json.dumps(item) for item in items)


def test_codex_usage_counts_cache_once_and_preserves_unknown():
    answer, usage = parse_codex_events(events('hello', {
        'input_tokens': 100, 'cached_input_tokens': 80, 'output_tokens': 20,
        'reasoning_output_tokens': 10,
    }))
    assert answer == 'hello'
    assert usage == {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120,
                     'input_token_details': {'cache_read': 80}, 'output_token_details': {'reasoning': 10}}
    assert parse_codex_events(events('hello')) == ('hello', None)
    assert parse_codex_events(events('hello', {'input_tokens': -1, 'output_tokens': 20}))[1] is None
    assert parse_codex_events('not-json') == ('not-json', None)


def test_redaction_keeps_learning_content_but_removes_secrets_and_paths():
    data = {'messages': [HumanMessage(content='哈希表 /Users/alice/private.py sk-secret123 abcdefgh123')],
            'api_key': 'hidden', 'serialized': {'internal': 'object'},
            'extra': {'runtime': {'cwd': '/tmp/private'}, 'metadata': {'phase': 'coaching'}}}
    clean = redact(data, ('abcdefgh123',))
    text = json.dumps(clean, ensure_ascii=False)
    assert '哈希表' in text and 'coaching' in text
    assert all(s not in text for s in ('alice', 'sk-secret123', 'abcdefgh123', 'hidden', 'internal', 'cwd'))
    assert isinstance(data['messages'][0], HumanMessage)  # original data untouched


def test_redaction_applies_to_run_envelopes(monkeypatch):
    create, update = Mock(), Mock()
    monkeypatch.setattr(Client, 'create_run', create)
    monkeypatch.setattr(Client, 'update_run', update)
    client = RedactingClient(api_key='test-key', secrets=('private-value',), auto_batch_tracing=False)
    client.create_run('test', inputs={'text': 'private-value'}, run_type='chain')
    client.update_run('id', error='Bearer token123 /Users/name/file', extra={'metadata': {'secret': 'value'}})
    assert create.call_args.kwargs['inputs']['text'] == '[REDACTED]'
    assert 'token123' not in update.call_args.kwargs['error']
    assert update.call_args.kwargs['extra']['metadata']['secret'] == '[REDACTED]'


def test_tracing_disabled_without_key_and_env_overrides_file(tmp_path, monkeypatch):
    monkeypatch.delenv('LANGSMITH_API_KEY', raising=False)
    monkeypatch.setenv('LANGSMITH_TRACING', 'true')
    assert get_observer(tmp_path) is None
    get_observer.cache_clear()
    (tmp_path / '.env.local').write_text('LANGSMITH_API_KEY=test-key\nLANGSMITH_TRACING=true\n')
    monkeypatch.setenv('LANGSMITH_TRACING', 'false')
    assert get_observer(tmp_path) is None


def test_codex_trace_records_validated_decision_and_usage(study_repo, monkeypatch):
    run = Mock()
    captured = {}

    class Observer:
        @contextmanager
        def llm(self, prompt, metadata):
            captured.update(prompt=prompt, metadata=metadata)
            yield run

    monkeypatch.setattr('leetcode_coach.engines.get_observer', lambda root: Observer())
    def runner(command, **kwargs):
        assert '--json' in command
        return subprocess.CompletedProcess(command, 0, events(json.dumps({'action': 'hint', 'response': '想想哈希表'}),
                       {'input_tokens': 10, 'output_tokens': 5}), '')
    engine = CodexCliDecisionEngine(StudyService(study_repo), executable=sys.executable, runner=runner)
    assert engine.decide({'messages': [HumanMessage(content='提示')]}).action == 'hint'
    outputs = run.end.call_args.kwargs['outputs']
    assert outputs['usage_metadata']['total_tokens'] == 15
    assert outputs['decision']['response'] == '想想哈希表'
    assert captured['metadata']['engine'] == 'codex-cli'


def test_invalid_codex_decision_is_error_in_trace(study_repo, monkeypatch):
    run = Mock()
    class Observer:
        @contextmanager
        def llm(self, *args):
            yield run
    monkeypatch.setattr('leetcode_coach.engines.get_observer', lambda root: Observer())
    engine = CodexCliDecisionEngine(StudyService(study_repo), executable=sys.executable,
        runner=lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, events('not valid JSON'), ''))
    assert engine.decide({}).action == 'continue'
    assert run.end.call_args.kwargs['error']
    assert run.end.call_args.kwargs['outputs']['usage_available'] is False


def test_graph_and_codex_trace_share_parent_and_thread(monkeypatch):
    from langgraph.graph import StateGraph, START, END
    from langchain_core.tracers.langchain import wait_for_all_tracers
    from typing import TypedDict

    class State(TypedDict):
        message: str

    client = RedactingClient(api_key='test-key', auto_batch_tracing=False)
    created, updated = [], []
    monkeypatch.setattr(client, 'create_run', lambda *a, **kw: created.append(kw))
    monkeypatch.setattr(client, 'update_run', lambda *a, **kw: updated.append(kw))
    observer = Observer(client, 'test-project')

    def decide(state):
        with observer.llm('synthetic prompt', {'engine': 'codex-cli'}) as run:
            run.end(outputs={'usage_available': False})
        return {'message': 'done'}

    graph = StateGraph(State)
    graph.add_node('process_turn', decide)
    graph.add_edge(START, 'process_turn')
    graph.add_edge('process_turn', END)
    graph.compile().invoke({'message': 'test'}, config={
        'callbacks': observer.callbacks(), 'configurable': {'thread_id': 'test-thread'}})
    wait_for_all_tracers()
    model_run = next(run for run in created if run['name'] == 'codex.decision')
    parent = next(run for run in created if run['name'] == 'process_turn')
    assert model_run['parent_run_id'] == parent['id']
    assert model_run['trace_id'] == parent['trace_id']
    assert parent['extra']['metadata']['thread_id'] == 'test-thread'
