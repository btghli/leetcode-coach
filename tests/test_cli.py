from pathlib import Path

from langchain.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from leetcode_coach.cli import _stream_graph, main
from leetcode_coach.graph import TrainingGraph
from leetcode_coach.schemas import ProblemMetadata, TeachBackDecision, TurnDecision
from leetcode_coach.services import MetadataResolver, PatternSweepService, StudyService


class NoopEngine:
    def decide(self, state):
        return TurnDecision(action="quit", response="done")

    def assess_teach_back(self, state):
        return TeachBackDecision.model_validate({
            "response": "incomplete",
            "assessment": {
                "invariant_correct": False,
                "complexity_correct": False,
                "edge_case_identified": False,
                "pattern_boundary_understood": False,
                "suggested_quality": 0,
                "feedback": "incomplete",
            },
        })


def test_cli_offline_commands(study_repo, capsys):
    assert main(["--root", str(study_repo), "status", "--brief"]) == 0
    assert "Problems initialized" in capsys.readouterr().out
    assert main(["--root", str(study_repo), "plan"]) == 0


async def test_v2_streaming_returns_graph_state(study_repo, capsys):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy", lists=["example"]))
    graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep), NoopEngine()).build(InMemorySaver())
    output = await _stream_graph(graph, {"messages": []}, {"configurable": {"thread_id": "stream-thread"}})
    assert output.value["phase"] == "coaching"
    assert "stage:" in capsys.readouterr().out


async def test_sqlite_checkpoint_resumes_across_graph_instances(study_repo, tmp_path):
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy", lists=["example"]))
    database = tmp_path / "checkpoint.sqlite"
    config = {"configurable": {"thread_id": "resume-thread"}}
    async with AsyncSqliteSaver.from_conn_string(str(database)) as saver:
        graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep), NoopEngine()).build(saver)
        started = await graph.ainvoke({"messages": []}, config=config, version="v2")
        assert started.value["selected_problem"]["slug"] == "two-sum"
    async with AsyncSqliteSaver.from_conn_string(str(database)) as saver:
        graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep), NoopEngine()).build(saver)
        resumed = await graph.ainvoke({"messages": [HumanMessage(content="/quit")]}, config=config, version="v2")
        assert resumed.value["phase"] == "complete"
