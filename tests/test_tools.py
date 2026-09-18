from leetcode_coach.schemas import ProblemMetadata
from leetcode_coach.services import PatternSweepService, StudyService
from leetcode_coach.tools import build_read_tools


def test_read_tools_are_narrow_and_typed(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy"))
    tools = {tool.name: tool for tool in build_read_tools(study, sweep)}
    assert set(tools) == {
        "get_study_status", "plan_study_day", "get_next_problem",
        "get_problem_context", "get_pattern_context", "summarize_recent_mistakes",
    }
    assert tools["get_problem_context"].invoke({"slug": "two-sum"})["metadata"]["id"] == 1
