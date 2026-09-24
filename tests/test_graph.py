from __future__ import annotations

from langchain.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from leetcode_coach import study_store
from leetcode_coach.chat_commands import (
    accepted_command,
    approval_command,
    next_problem_command,
    routing_mode_command,
)
from leetcode_coach.graph import TrainingGraph, _last_human_text
from leetcode_coach.schemas import ProblemMetadata, TeachBackAssessment, TeachBackDecision, TurnDecision
from leetcode_coach.services import MetadataResolver, PatternSweepService, StudyService


class FakeEngine:
    def __init__(self):
        self.calls = 0

    def decide(self, state):
        self.calls += 1
        return TurnDecision(action="hint", response="先考虑已经看过的数字。")

    def assess_teach_back(self, state):
        return TeachBackDecision(
            response="讲解完整，可以记录。",
            assessment=TeachBackAssessment(
                invariant_correct=True,
                complexity_correct=True,
                edge_case_identified=True,
                pattern_boundary_understood=True,
                suggested_quality=5,
                feedback="完整",
            ),
        )


class SwitchModeEngine:
    def __init__(self, requested_mode="pattern-sweep"):
        self.requested_mode = requested_mode

    def decide(self, state):
        return TurnDecision(
            action="switch_mode",
            requested_mode=self.requested_mode,
            response="请求切换选题模式。",
        )

    def assess_teach_back(self, state):
        raise AssertionError("mode-switch test must not assess teach-back")


class JudgeFailureEngine(FakeEngine):
    def decide(self, state):
        return TurnDecision(action="judge_failed", judge_failure="WA", response="先检查最小失败样例。")


def test_explicit_mode_commands_are_deterministic():
    assert routing_mode_command("切换到题型扫荡模式") == "pattern-sweep"
    assert routing_mode_command("我要使用 pattern sweep") == "pattern-sweep"
    assert routing_mode_command("退出题型扫荡模式") == "auto"
    assert routing_mode_command("切换到自动选题模式") == "auto"
    assert routing_mode_command("什么是题型扫荡模式？") is None


def test_agent_chat_content_blocks_are_normalized_before_commands():
    state = {"messages": [HumanMessage(content=[{"type": "text", "text": "/sweep"}])]}
    assert _last_human_text(state) == "/sweep"
    assert TrainingGraph.route_start(state) == "turn"


def test_idle_checkpoint_does_not_replay_last_human_turn():
    assert TrainingGraph.route_start({
        "messages": [HumanMessage(content="提示"), AIMessage(content="先想哈希表")],
        "phase": "coaching",
        "selected_problem": {"slug": "two-sum"},
    }) == "end"


def test_accepted_judge_reports_are_deterministic():
    assert accepted_command("/ac")
    assert accepted_command("19 ac 了")
    assert accepted_command("#19 AC了")
    assert accepted_command("提交通过了")
    assert accepted_command("too many questiones. No 19 got ac")
    assert accepted_command("I got AC")
    assert not accepted_command("还没 ac")
    assert not accepted_command("I did not get ac")
    assert not accepted_command("AC 是什么意思？")


def test_chat_approval_requires_an_explicit_command():
    assert approval_command("批准") == "approve"
    assert approval_command("/approve") == "approve"
    assert approval_command("拒绝") == "reject"
    assert approval_command("下一题") is None


def test_coaching_remains_model_driven_after_multiple_turns(study_repo):
    engine = FakeEngine()
    training = TrainingGraph(
        StudyService(study_repo), PatternSweepService(study_repo), MetadataResolver(StudyService(study_repo), PatternSweepService(study_repo)), engine,
    )
    state = {
        "phase": "coaching", "hint_level": 2,
        "messages": [HumanMessage(content="我准备写代码")],
    }
    result = training.process_turn(state)
    assert engine.calls == 1
    assert "已经看过的数字" in result["messages"][0].content


def test_next_problem_is_a_narrow_explicit_control():
    assert next_problem_command("下一题")
    assert next_problem_command("next problem")
    assert not next_problem_command("我做过多少题？")
    assert TrainingGraph.route_start({
        "messages": [HumanMessage(content="我做过多少题？")],
    }) == "turn"
    assert TrainingGraph.route_start({
        "messages": [HumanMessage(content="我做过多少题？")],
        "phase": "complete",
        "selected_problem": {"slug": "two-sum"},
    }) == "turn"
    assert TrainingGraph.route_start({
        "messages": [HumanMessage(content="下一题")],
        "phase": "complete",
        "selected_problem": {"slug": "two-sum"},
    }) == "load"
    assert TrainingGraph.route_start({
        "messages": [HumanMessage(content="下一题")],
        "phase": "awaiting_approval",
        "selected_problem": {"slug": "two-sum"},
        "teach_back_assessment": {"invariant_correct": True},
        "pending_action": {
            "action": "archive_solution",
            "arguments": {"slug": "two-sum"},
            "description": "legacy archive",
        },
    }) == "migrate"


def test_unknown_legacy_pending_action_is_migrated():
    assert TrainingGraph.route_start({
        "messages": [HumanMessage(content="继续")],
        "pending_action": {
            "action": "session_summary",
            "arguments": {},
            "description": "unknown legacy write",
        },
    }) == "migrate"


async def test_legacy_pending_write_is_normalized_to_one_grouped_preview(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy"))
    graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep), FakeEngine()).build(InMemorySaver())

    result = await graph.ainvoke({
        "messages": [HumanMessage(content="继续")],
        "phase": "awaiting_approval",
        "selected_problem": {"slug": "two-sum", "title": "Two Sum"},
        "training_mode": "guided-solve",
        "judge_result": "AC",
        "teach_back_assessment": {
            "invariant_correct": True,
            "complexity_correct": True,
            "edge_case_identified": True,
            "pattern_boundary_understood": True,
            "suggested_quality": 4,
            "feedback": "完整",
        },
        "pending_action": {
            "action": "archive_solution",
            "arguments": {"slug": "two-sum"},
            "description": "legacy archive",
        },
    }, config={"configurable": {"thread_id": "legacy-normalization"}}, version="v2")

    assert result.interrupts
    assert result.value["pending_action"]["action"] == "complete_attempt"


async def test_full_training_loop_with_interrupt(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(
        id=1, slug="two-sum", title="Two Sum", difficulty="Easy", lists=["example"],
    ))
    graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep), FakeEngine()).build(InMemorySaver())
    config = {"configurable": {"thread_id": "test-thread"}}

    started = await graph.ainvoke({"messages": [], "thread_id": "test-thread"}, config=config, version="v2")
    assert started.value["phase"] == "coaching"
    assert type(started.value["phase"]) is str
    hinted = await graph.ainvoke({"messages": [HumanMessage(content="给一点提示")]}, config=config, version="v2")
    assert hinted.value["hint_level"] == 1
    accepted = await graph.ainvoke({"messages": [HumanMessage(content="/ac")]}, config=config, version="v2")
    assert accepted.value["phase"] == "teach_back"
    pending = await graph.ainvoke({"messages": [HumanMessage(content="不变量、复杂度、边界和不适用条件都解释完了")]}, config=config, version="v2")
    assert pending.interrupts
    assert pending.value["pending_action"]["action"] == "complete_attempt"
    completed = await graph.ainvoke(Command(resume={"type": "approve"}), config=config, version="v2")
    assert not completed.interrupts
    assert completed.value["phase"] == "complete"
    assert study.problem_context("two-sum")["metadata"]["mastery"] == "solid"


async def test_selection_resumes_in_progress_before_due_review(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    for metadata in (
        ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy", lists=["example"]),
        ProblemMetadata(id=49, slug="group-anagrams", title="Group Anagrams", difficulty="Medium", lists=["example"]),
    ):
        study.initialize_problem(metadata)
    due_note = study.repository.find("group-anagrams")[0]
    open_note = study.repository.find("two-sum")[0]
    study_store.update_note_meta(due_note, {"status": "AC", "next_review": "2020-01-01"})
    study_store.update_note_meta(open_note, {"status": "Doing"})
    graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep), FakeEngine()).build(InMemorySaver())

    result = await graph.ainvoke({"messages": []}, config={"configurable": {"thread_id": "resume-first"}}, version="v2")

    assert result.value["selected_problem"]["slug"] == "two-sum"
    assert result.value["training_mode"] == "guided-solve"


async def test_judge_failures_survive_later_ac_and_are_persisted(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(
        id=1, slug="two-sum", title="Two Sum", difficulty="Easy", lists=["example"],
    ))
    graph = TrainingGraph(
        study,
        sweep,
        MetadataResolver(study, sweep),
        JudgeFailureEngine(),
    ).build(InMemorySaver())
    config = {"configurable": {"thread_id": "judge-history"}}

    await graph.ainvoke({"messages": []}, config=config, version="v2")
    failed = await graph.ainvoke(
        {"messages": [HumanMessage(content="提交后是 WA")]},
        config=config,
        version="v2",
    )
    assert failed.value["judge_result"] == "WA"
    assert failed.value["judge_failures"] == ["WA"]

    accepted = await graph.ainvoke(
        {"messages": [HumanMessage(content="/ac")]},
        config=config,
        version="v2",
    )
    assert accepted.value["judge_result"] == "AC"
    assert accepted.value["judge_failures"] == ["WA"]

    pending = await graph.ainvoke(
        {"messages": [HumanMessage(content="完整讲解 invariant、复杂度、边界和不适用条件")]},
        config=config,
        version="v2",
    )
    attempt = pending.value["pending_action"]["arguments"]["attempt"]
    assert attempt["judge_failures"] == ["WA"]
    assert attempt["first_try_ac"] is False


async def test_reject_does_not_write(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy", lists=["example"]))
    graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep), FakeEngine()).build(InMemorySaver())
    config = {"configurable": {"thread_id": "reject-thread"}}
    await graph.ainvoke({"messages": []}, config=config, version="v2")
    await graph.ainvoke({"messages": [HumanMessage(content="/ac")]}, config=config, version="v2")
    pending = await graph.ainvoke({"messages": [HumanMessage(content="完整讲解")]}, config=config, version="v2")
    assert pending.interrupts
    rejected = await graph.ainvoke(Command(resume={"type": "reject"}), config=config, version="v2")
    assert rejected.value["phase"] == "coaching"
    assert study.problem_context("two-sum")["metadata"]["status"] == "Todo"


async def test_chat_message_during_approval_gets_visible_notice(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy", lists=["example"]))
    graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep), FakeEngine()).build(InMemorySaver())
    config = {"configurable": {"thread_id": "pending-chat-notice"}}

    await graph.ainvoke({"messages": []}, config=config, version="v2")
    await graph.ainvoke({"messages": [HumanMessage(content="/ac")]}, config=config, version="v2")
    pending = await graph.ainvoke({"messages": [HumanMessage(content="完整讲解")]}, config=config, version="v2")
    assert pending.interrupts

    repeated = await graph.ainvoke({"messages": [HumanMessage(content="下一题")]}, config=config, version="v2")

    assert repeated.interrupts
    assert repeated.value["phase"] == "awaiting_approval"
    assert repeated.value["pending_action"]["action"] == "complete_attempt"
    assert "还不能进入下一题" in repeated.value["messages"][-1].content
    assert study.problem_context("two-sum")["metadata"]["status"] == "Todo"

    approved = await graph.ainvoke({"messages": [HumanMessage(content="批准")]}, config=config, version="v2")
    assert not approved.interrupts
    assert approved.value["attempt_recorded"] is True
    assert approved.value["pending_action"] is None
    assert approved.value["phase"] == "complete"
    assert study.problem_context("two-sum")["metadata"]["status"] == "AC"


def test_unified_completion_rolls_back_every_protected_write_on_failure(study_repo, monkeypatch):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy"))
    before = {
        path.relative_to(study_repo): path.read_bytes()
        for root in (study_repo / "problems", study_repo / "study", study_repo / "knowledge")
        for path in root.rglob("*")
        if path.is_file()
    }

    def fail_sync():
        raise RuntimeError("simulated sync failure")

    monkeypatch.setattr(sweep, "sync", fail_sync)
    result = TrainingGraph(study, sweep, MetadataResolver(study, sweep), FakeEngine()).persist({
        "pending_action": {
            "action": "complete_attempt",
            "arguments": {
                "attempt": {
                    "slug": "two-sum",
                    "mastery": "solid",
                    "mode": "guided-solve",
                    "quality": 5,
                    "hint_level": 0,
                    "judge_failures": [],
                    "teach_back": True,
                },
                "archive_solution": False,
                "sync_pattern_sweep": True,
                "log_session": True,
            },
        },
    })
    after = {
        path.relative_to(study_repo): path.read_bytes()
        for root in (study_repo / "problems", study_repo / "study", study_repo / "knowledge")
        for path in root.rglob("*")
        if path.is_file()
    }

    assert "simulated sync failure" in result["last_error"]
    assert before == after
    assert study.problem_context("two-sum")["metadata"]["status"] == "Todo"


async def test_switch_to_pattern_sweep_reselects_and_persists_mode(study_repo, monkeypatch):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy"))
    item = {
        "kind": "sweep",
        "category": {"slug": "array-hash", "title": "数组与哈希"},
        "subpattern": {"slug": "frequency-index", "title": "计数与索引"},
        "problem": {"slug": "two-sum", "title": "Two Sum"},
    }
    monkeypatch.setattr(sweep, "recommend_next", lambda: item)
    monkeypatch.setattr(sweep, "pattern_card", lambda slug: {
        "slug": slug,
        "title": "数组与哈希",
        "subpatterns": [{"slug": "frequency-index", "title": "计数与索引"}],
        "content": "# 数组与哈希模式卡\n\n先识别键和值。",
    })
    graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep), SwitchModeEngine()).build(InMemorySaver())
    config = {"configurable": {"thread_id": "switch-mode-thread"}}

    started = await graph.ainvoke({"messages": []}, config=config, version="v2")
    assert started.value["training_mode"] == "guided-solve"
    switched = await graph.ainvoke(
        {"messages": [HumanMessage(content="切换到题型扫荡模式")]}, config=config, version="v2",
    )

    assert switched.value["routing_mode"] == "pattern-sweep"
    assert switched.value["selected_problem"] is None
    assert switched.value["sweep_card_category"] == "array-hash"
    assert switched.value["phase"] == "pattern_card"
    assert "数组与哈希模式卡" in switched.value["messages"][-1].content

    continued = await graph.ainvoke(
        {"messages": [HumanMessage(content="继续")]}, config=config, version="v2",
    )
    assert continued.value["selected_problem"]["slug"] == "two-sum"
    assert continued.value["training_mode"] == "pattern-contrast"
    assert continued.value["phase"] == "coaching"
    assert "小模式：计数与索引" in continued.value["messages"][-1].content


async def test_first_message_can_switch_to_pattern_sweep_before_bootstrap(study_repo, monkeypatch):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    item = {
        "kind": "sweep",
        "category": {"slug": "linked-list", "title": "链表"},
        "subpattern": {"slug": "fixed-gap", "title": "固定间距与 dummy"},
        "problem": {"slug": "remove-nth-node-from-end-of-list", "title": "Remove Nth Node From End of List"},
    }
    monkeypatch.setattr(sweep, "recommend_next", lambda: item)
    monkeypatch.setattr(sweep, "pattern_card", lambda slug: {
        "slug": slug,
        "title": "链表",
        "subpatterns": [{"slug": "fixed-gap", "title": "固定间距与 dummy"}],
        "content": "# 链表模式卡",
    })
    graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep), FakeEngine()).build(InMemorySaver())

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="切换到题型扫荡模式")]},
        config={"configurable": {"thread_id": "first-message-switch"}}, version="v2",
    )

    assert result.value["routing_mode"] == "pattern-sweep"
    assert result.value["phase"] == "pattern_card"
    assert result.value["selected_problem"] is None
    assert result.value["sweep_category"]["slug"] == "linked-list"
    assert "链表模式卡" in result.value["messages"][-1].content


async def test_pattern_sweep_mode_bypasses_due_review(study_repo, monkeypatch):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    due = {"slug": "two-sum", "title": "Two Sum", "reason": "due-review", "status": "Review"}
    monkeypatch.setattr(study, "status", lambda: {"due_reviews": [due]})
    new_problem = {"slug": "group-anagrams", "title": "Group Anagrams"}
    monkeypatch.setattr(study, "problem_context", lambda slug: {"metadata": new_problem, "note": ""})
    monkeypatch.setattr(sweep, "recommend_next", lambda: {
        "kind": "sweep",
        "category": {"slug": "array-hash", "title": "数组与哈希"},
        "subpattern": {"slug": "frequency-index", "title": "计数与索引"},
        "problem": new_problem,
    })
    graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep), FakeEngine()).build(InMemorySaver())

    result = await graph.ainvoke(
        {"messages": [], "routing_mode": "pattern-sweep", "sweep_card_category": "array-hash"},
        config={"configurable": {"thread_id": "due-first-thread"}}, version="v2",
    )

    assert result.value["selected_problem"]["slug"] == "group-anagrams"
    assert result.value["training_mode"] == "pattern-contrast"
    assert result.value["routing_mode"] == "pattern-sweep"


def test_pattern_sweep_discards_stale_normal_selection():
    assert TrainingGraph.route_start({
        "routing_mode": "pattern-sweep",
        "phase": "coaching",
        "selected_problem": {"slug": "group-anagrams", "reason": "due-review"},
    }) == "load"


async def test_incomplete_assessment_cannot_claim_completion_in_prose(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy"))

    class MisleadingEngine(FakeEngine):
        def assess_teach_back(self, state):
            return TeachBackDecision(
                response="复盘通过，可以进入下一题。",
                assessment=TeachBackAssessment(
                    invariant_correct=True,
                    complexity_correct=True,
                    edge_case_identified=False,
                    pattern_boundary_understood=False,
                    suggested_quality=2,
                    feedback="仍缺少边界。",
                ),
            )

    graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep), MisleadingEngine()).build(InMemorySaver())
    config = {"configurable": {"thread_id": "semantic-guard"}}
    await graph.ainvoke({"messages": []}, config=config, version="v2")
    await graph.ainvoke({"messages": [HumanMessage(content="/ac")]}, config=config, version="v2")
    result = await graph.ainvoke({"messages": [HumanMessage(content="我的复盘")]}, config=config, version="v2")

    assert result.value["phase"] == "teach_back"
    assert result.value["teach_back_assessment"]["edge_case_identified"] is False
    assert result.value.get("pending_action") is None
    assert study.problem_context("two-sum")["metadata"]["status"] == "Todo"


def test_next_subpattern_is_guarded_until_persistence(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    training = TrainingGraph(study, sweep, MetadataResolver(study, sweep), FakeEngine())
    updates = training.process_turn({
        "messages": [HumanMessage(content="继续下一个小模式")],
        "phase": "coaching",
        "judge_result": "AC",
        "routing_mode": "pattern-sweep",
        "selected_problem": {"slug": "two-sum", "reason": "pattern-sweep"},
        "teach_back_assessment": {
            "invariant_correct": True,
            "complexity_correct": True,
            "edge_case_identified": True,
            "pattern_boundary_understood": True,
        },
        "attempt_recorded": False,
    })
    assert updates["phase"] == "teach_back"
    assert updates["last_error"] == "subpattern_advance_guard"
    assert "还不能进入" in updates["messages"][0].content


async def test_old_ac_text_is_not_recovered_for_a_later_turn(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(id=19, slug="remove-nth-node-from-end-of-list", title="Remove Nth Node", difficulty="Medium"))
    graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep), FakeEngine()).build(InMemorySaver())

    result = await graph.ainvoke({
        "messages": [
            HumanMessage(content="too many questions. No 19 got ac"),
            HumanMessage(content="delete head; fixed distance does not apply to cycle detection"),
        ],
        "phase": "coaching",
        "routing_mode": "pattern-sweep",
        "training_mode": "pattern-contrast",
        "selected_problem": {
            "id": 19,
            "slug": "remove-nth-node-from-end-of-list",
            "title": "Remove Nth Node",
            "reason": "pattern-sweep",
        },
        "judge_result": None,
    }, config={"configurable": {"thread_id": "recover-english-ac"}}, version="v2")

    assert not result.interrupts
    assert result.value["judge_result"] is None
    assert result.value["phase"] == "coaching"
    assert result.value.get("pending_action") is None


async def test_teach_back_uses_one_model_call_and_emits_one_reply(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy"))

    class CountingEngine(FakeEngine):
        def __init__(self):
            super().__init__()
            self.assessment_calls = 0

        def assess_teach_back(self, state):
            self.assessment_calls += 1
            return TeachBackDecision(
                action="teach_back",
                response="只补充复杂度。",
                assessment=TeachBackAssessment(
                    invariant_correct=True,
                    complexity_correct=False,
                    edge_case_identified=False,
                    pattern_boundary_understood=False,
                    suggested_quality=1,
                    feedback="证据不完整",
                ),
            )

    engine = CountingEngine()
    graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep), engine).build(InMemorySaver())
    config = {"configurable": {"thread_id": "single-teach-back-call"}}
    await graph.ainvoke({"messages": []}, config=config, version="v2")
    await graph.ainvoke({"messages": [HumanMessage(content="/ac")]}, config=config, version="v2")
    result = await graph.ainvoke({"messages": [HumanMessage(content="不变量是已经处理的元素都已分组")]}, config=config, version="v2")

    assert engine.calls == 0
    assert engine.assessment_calls == 1
    assert result.value["messages"][-1].content == "只补充复杂度。"
    assert result.value["messages"][-2].content == "不变量是已经处理的元素都已分组"


def test_teach_back_question_does_not_replace_existing_assessment(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)

    class QuestionEngine(FakeEngine):
        def assess_teach_back(self, state):
            return TeachBackDecision(
                action="continue",
                response="不变量就是每一步都保持成立的性质。",
                assessment=TeachBackAssessment(
                    invariant_correct=False,
                    complexity_correct=False,
                    edge_case_identified=False,
                    pattern_boundary_understood=False,
                    suggested_quality=0,
                    feedback="这不是新证据",
                ),
            )

    existing = {
        "invariant_correct": True,
        "complexity_correct": False,
        "edge_case_identified": False,
        "pattern_boundary_understood": False,
        "suggested_quality": 1,
        "feedback": "已说明不变量",
    }
    updates = TrainingGraph(study, sweep, MetadataResolver(study, sweep), QuestionEngine()).process_turn({
        "phase": "teach_back",
        "judge_result": "AC",
        "teach_back_assessment": existing,
        "messages": [HumanMessage(content="什么是不变量？")],
    })

    assert updates["phase"] == "teach_back"
    assert "teach_back_assessment" not in updates
    assert "不变量" in updates["messages"][0].content


async def test_auto_routing_does_not_fall_through_to_pattern_sweep(study_repo, monkeypatch):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    monkeypatch.setattr(study, "next_problem", lambda: None)
    monkeypatch.setattr(sweep, "recommend_next", lambda: {
        "category": {"slug": "array-hash", "title": "数组与哈希"},
        "subpattern": {"slug": "frequency-index", "title": "计数与索引"},
        "problem": {"slug": "two-sum", "title": "Two Sum"},
    })
    graph = TrainingGraph(study, sweep, MetadataResolver(study, sweep), FakeEngine()).build(InMemorySaver())

    result = await graph.ainvoke(
        {"messages": [], "routing_mode": "auto"},
        config={"configurable": {"thread_id": "auto-is-not-sweep"}},
        version="v2",
    )

    assert result.value["phase"] == "complete"
    assert result.value["selected_problem"] is None
