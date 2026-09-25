from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from langchain.messages import AIMessage, HumanMessage

from leetcode_coach.engines import (
    CODEX_DECISION_INSTRUCTIONS,
    TEACH_BACK_INSTRUCTIONS,
    CodexCliDecisionEngine,
    build_decision_context,
    build_study_summary,
    codex_output_schema,
    strict_output_schema,
)
from leetcode_coach.schemas import ProblemMetadata, TeachBackDecision
from leetcode_coach.services import StudyService


def test_codex_cli_engine_is_ephemeral_read_only_and_structured(study_repo: Path):
    study = StudyService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy"))
    observed: dict = {}

    def fake_runner(command, **kwargs):
        observed.update(command=command, kwargs=kwargs)
        output = {
            "action": "hint",
            "response": "先考虑用一个集合记录已经见过的值。",
            "judge_failure": None,
            "requested_mode": None,
        }
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(output), stderr="")

    engine = CodexCliDecisionEngine(study, executable=sys.executable, runner=fake_runner)
    decision = engine.decide({
        "phase": "coaching",
        "selected_problem": {"slug": "two-sum", "title": "Two Sum"},
        "training_mode": "guided-solve",
        "hint_level": 0,
        "messages": [AIMessage(content="先说明暴力解法。"), HumanMessage(content="我想用哈希表。")],
    })

    assert decision.action == "hint"
    command = observed["command"]
    assert "--ephemeral" in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert "--ignore-user-config" in command
    assert "--ignore-rules" in command
    assert "--output-schema" in command
    assert observed["kwargs"]["cwd"] != study_repo
    assert "我想用哈希表" in observed["kwargs"]["input"]
    assert '"problem_count": 1' in observed["kwargs"]["input"]
    assert '"routing_mode": "auto"' in observed["kwargs"]["input"]
    assert observed["kwargs"]["capture_output"] is True


def test_codex_cli_engine_rejects_invalid_structured_output(study_repo: Path):
    def fake_runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="not-json", stderr="")

    engine = CodexCliDecisionEngine(
        StudyService(study_repo), executable=sys.executable, runner=fake_runner,
    )
    decision = engine.decide({"phase": "coaching", "messages": [HumanMessage(content="提示")]})
    assert decision.action == "continue"
    assert "schema" in decision.response


def test_codex_cli_failure_is_actionable_and_does_not_raise(study_repo: Path):
    def fake_runner(command, **kwargs):
        stderr = '{\n  "error": {\n    "message": "authentication required"\n  }\n}\n'
        return subprocess.CompletedProcess(command, 7, stdout="", stderr=stderr)

    engine = CodexCliDecisionEngine(
        StudyService(study_repo), executable=sys.executable, runner=fake_runner,
    )
    decision = engine.decide({"phase": "coaching", "messages": [HumanMessage(content="提示")]})
    assert decision.action == "continue"
    assert "exit 7" in decision.response
    assert "authentication required" in decision.response


def test_codex_schema_is_strict_for_every_object():
    schema = codex_output_schema()

    def assert_strict(value):
        if isinstance(value, dict):
            if value.get("type") == "object" or "properties" in value:
                assert value["additionalProperties"] is False
                assert set(value["required"]) == set(value.get("properties", {}))
            for child in value.values():
                assert_strict(child)
        elif isinstance(value, list):
            for child in value:
                assert_strict(child)

    assert_strict(schema)
    assert "switch_mode" in schema["properties"]["action"]["enum"]
    assert "select_next" in schema["properties"]["action"]["enum"]
    assert_strict(strict_output_schema(TeachBackDecision))


def test_decision_context_has_only_bounded_recent_messages(study_repo: Path):
    messages = [HumanMessage(content=f"message-{index}") for index in range(20)]
    context = build_decision_context({"phase": "coaching", "messages": messages}, StudyService(study_repo))
    assert len(context.recent_messages) == 4
    assert context.recent_messages[0]["content"] == "message-16"
    assert context.learner_message == "message-19"


def test_codex_prompt_uses_compact_decision_instructions(study_repo: Path):
    context = build_decision_context({"phase": "coaching", "messages": [HumanMessage(content="提示")]}, StudyService(study_repo))
    prompt = CodexCliDecisionEngine._prompt(context)
    assert CODEX_DECISION_INSTRUCTIONS in prompt
    assert "Use progressive disclosure" not in prompt
    assert "do not split one understood concept" in prompt
    assert "redo-from-memory" in prompt


def test_teach_back_prompt_avoids_retesting_supported_evidence(study_repo: Path):
    context = build_decision_context(
        {
            "phase": "teach_back",
            "judge_result": "AC",
            "messages": [HumanMessage(content="计数键是字符频次元组，复杂度 O(nk)")],
        },
        StudyService(study_repo),
    )

    prompt = CodexCliDecisionEngine._teach_back_prompt(context)

    assert TEACH_BACK_INSTRUCTIONS in prompt
    assert "never ask the learner to restate them" in prompt
    assert "at most two short sentences" in prompt
    assert "half-finished sentence with one blank" in prompt


def test_decision_context_truncates_oversized_message(study_repo: Path):
    context = build_decision_context(
        {"phase": "coaching", "messages": [HumanMessage(content="x" * 10_000)]},
        StudyService(study_repo),
    )
    assert len(context.learner_message) < 2_000
    assert context.learner_message.endswith("[truncated]")


def test_decision_context_normalizes_agent_chat_content_blocks(study_repo: Path):
    context = build_decision_context(
        {"phase": "coaching", "messages": [HumanMessage(content=[{"type": "text", "text": "/sweep"}])]},
        StudyService(study_repo),
    )
    assert context.learner_message == "/sweep"


def test_codex_uses_phase_specific_teach_back_schema(study_repo: Path):
    observed: dict = {}

    def fake_runner(command, **kwargs):
        observed.update(command=command, kwargs=kwargs)
        output = {
            "action": "teach_back",
            "assessment": {
                "invariant_correct": True,
                "complexity_correct": True,
                "edge_case_identified": False,
                "pattern_boundary_understood": False,
                "suggested_quality": 2,
                "feedback": "还缺边界。",
            },
            "response": "请补充边界。",
        }
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(output), stderr="")

    engine = CodexCliDecisionEngine(StudyService(study_repo), executable=sys.executable, runner=fake_runner)
    decision = engine.assess_teach_back({
        "phase": "teach_back",
        "judge_result": "AC",
        "messages": [HumanMessage(content="复杂度是 O(n) / O(1)")],
    })

    assert decision.assessment.complete is False
    assert decision.response == "请补充边界。"
    assert "TeachBackDecision" in observed["kwargs"]["input"]


def test_teach_back_evidence_contains_only_human_messages_after_ac(study_repo: Path):
    context = build_decision_context({
        "phase": "teach_back",
        "teach_back_start_index": 2,
        "messages": [
            HumanMessage(content="旧题回答"),
            HumanMessage(content="/ac"),
            AIMessage(content="请开始复盘"),
            HumanMessage(content="不变量是已处理元素保持正确分组"),
        ],
    }, StudyService(study_repo))

    assert context.teach_back_evidence == ["不变量是已处理元素保持正确分组"]


def test_study_summary_exposes_progress_counts_without_root_path(study_repo: Path):
    study = StudyService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy"))
    summary = build_study_summary(study)
    assert summary["problem_count"] == 1
    assert summary["status_counts"]["Todo"] == 1
    assert "root" not in summary


def test_study_summary_strips_paths_and_attempt_details(study_repo: Path):
    study = StudyService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy"))
    summary = build_study_summary(study)
    for item in [*summary["due_reviews"], summary["recommended_next"], *summary["new_or_open"]]:
        assert "path" not in item
        assert "stats" not in item
        assert "mistake_tags" not in item
