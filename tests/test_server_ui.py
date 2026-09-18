from __future__ import annotations

import json

from langchain.messages import HumanMessage

from leetcode_coach.graph import LazyLangChainDecisionEngine
from leetcode_coach.services import PatternSweepService, StudyService
from leetcode_coach.ui import AGENT_CHAT_URL, DEPLOYMENT_URL, GRAPH_ID, _server_command


def test_langgraph_config_exports_chat_graph(repo_root):
    config = json.loads((repo_root / "langgraph.json").read_text(encoding="utf-8"))
    assert config["graphs"][GRAPH_ID] == "leetcode_coach.server:graph"
    assert DEPLOYMENT_URL == "http://localhost:2024"
    assert "assistantId=leetcode_coach" in AGENT_CHAT_URL
    assert "apiUrl=http%3A%2F%2Flocalhost%3A2024" in AGENT_CHAT_URL


def test_ui_launcher_prefers_project_virtualenv(repo_root):
    command = _server_command(repo_root)
    assert command[0] == str(repo_root / ".venv" / "bin" / "langgraph")
    assert command[-1] == "2024"


def test_lazy_engine_reports_missing_model_without_initializing_provider(study_repo, monkeypatch):
    monkeypatch.delenv("LEETCODE_COACH_MODEL", raising=False)
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    engine = LazyLangChainDecisionEngine(None, study, sweep)
    decision = engine.decide({"messages": [HumanMessage(content="提示")], "phase": "coaching"})
    assert decision.action == "continue"
    assert "模型尚未配置" in decision.response


def test_lazy_engine_turns_insufficient_quota_into_actionable_message(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    engine = LazyLangChainDecisionEngine(None, study, sweep)

    class QuotaError(Exception):
        code = "insufficient_quota"

    class FailingDelegate:
        def decide(self, state):
            raise QuotaError("quota exhausted")

    engine._delegate = FailingDelegate()
    decision = engine.decide({"messages": [HumanMessage(content="提示")], "phase": "coaching"})
    assert decision.action == "continue"
    assert "没有可用额度" in decision.response
