import pytest
from langgraph.checkpoint.memory import InMemorySaver

from leetcode_coach.graph import TrainingGraph
from leetcode_coach.schemas import ProblemMetadata, TurnDecision, TeachBackDecision, TeachBackAssessment
from leetcode_coach.services import StudyService, PatternSweepService, MetadataResolver
from leetcode_coach.web import Workbench


class Engine:
    def decide(self, state):
        return TurnDecision(action='hint', response='说明你的推导。')

    def assess_teach_back(self, state):
        return TeachBackDecision(response='证据完整', assessment=TeachBackAssessment(
            invariant_correct=True, complexity_correct=True, edge_case_identified=True,
            pattern_boundary_understood=True, suggested_quality=4, feedback='完整'))


@pytest.fixture
def workbench(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug='two-sum', title='Two Sum', difficulty='Easy', lists=['example']))
    return Workbench(study_repo, TrainingGraph(study, sweep, MetadataResolver(study, sweep), Engine()).build(InMemorySaver()))


def test_overview_is_read_only_and_includes_catalog(workbench, study_repo):
    before = {p: p.read_bytes() for p in study_repo.rglob('*') if p.is_file()}
    result = workbench.overview()
    assert result['status']['problem_count'] == 1
    assert set(result['plan']['daily_target']) == {'review', 'new'}
    assert len(result['categories']) == 18
    assert result['categories'][0]['content'] == '模板待补充'
    assert before == {p: p.read_bytes() for p in study_repo.rglob('*') if p.is_file()}


@pytest.mark.parametrize('streaming', [False, True])
async def test_workbench_approval_resume_and_dashboard_refresh(workbench, streaming):
    events = []
    sink = events.append if streaming else None
    await workbench.conversation('test', {'action':'start'}, sink)
    await workbench.conversation('test', {'action':'message', 'message':'/ac'}, sink)
    state = await workbench.conversation('test', {'action':'message', 'message':'完整复盘'}, sink)
    assert state['pending_action']['action'] == 'complete_attempt'
    assert workbench.overview()['status']['status_counts']['AC'] == 0
    restored = await workbench.conversation('test')
    assert set(restored['day_plan']['daily_target']) == {'review', 'new'}
    assert restored['pending_action'] == state['pending_action']
    done = await workbench.conversation('test', {'action':'approve'}, sink)
    assert done['attempt_recorded']
    assert workbench.overview()['status']['status_counts']['AC'] == 1
    with pytest.raises(ValueError):
        await workbench.conversation('test', {'action':'approve'})
    if streaming:
        assert any(event['type'] == 'stage' for event in events)


async def test_rejection_does_not_save(workbench):
    await workbench.conversation('test', {'action':'start'})
    await workbench.conversation('test', {'action':'message', 'message':'/ac'})
    await workbench.conversation('test', {'action':'message', 'message':'完整复盘'})
    await workbench.conversation('test', {'action':'reject'})
    assert workbench.overview()['status']['status_counts']['AC'] == 0


async def test_invalid_thread_and_action(workbench):
    with pytest.raises(ValueError):
        await workbench.conversation('../x')
    with pytest.raises(ValueError):
        await workbench.conversation('test', {'action':'delete'})


async def test_history_lists_each_thread_once(workbench):
    await workbench.conversation('first', {'action': 'start'})
    await workbench.conversation('first', {'action': 'message', 'message': '提示'})
    await workbench.conversation('second', {'action': 'start'})
    history = await workbench.threads()
    assert {entry['id'] for entry in history} == {'first', 'second'}
    assert len(history) == 2
    assert all(entry['title'] == 'Two Sum' for entry in history)


async def test_http_routes_and_same_origin_guard(workbench):
    import asyncio
    import json
    import threading
    from http.client import HTTPConnection
    from http.server import ThreadingHTTPServer
    from leetcode_coach.web import handler_for

    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(workbench, asyncio.get_running_loop()))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()

    def request(path, headers=None):
        client = HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        try:
            client.request('GET', path, headers=headers or {})
            response = client.getresponse()
            return response.status, response.read()
        finally:
            client.close()

    try:
        status, body = await asyncio.to_thread(request, '/')
        assert status == 200 and b'app.js' in body
        status, body = await asyncio.to_thread(request, '/api/overview')
        assert status == 200 and len(json.loads(body)['categories']) == 18
        status, _ = await asyncio.to_thread(request, '/api/overview', {'Origin': 'https://example.com'})
        assert status == 403
        status, _ = await asyncio.to_thread(request, '/api/overview', {'Host': 'example.com'})
        assert status == 403
        status, _ = await asyncio.to_thread(request, '/../study/profile.json')
        assert status == 404
    finally:
        await asyncio.to_thread(server.shutdown)
        server.server_close()
        worker.join()
