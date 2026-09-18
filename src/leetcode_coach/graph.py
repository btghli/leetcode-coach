"""The explicit LangGraph training lifecycle around a LangChain coaching agent."""

from __future__ import annotations

import asyncio
import re
from typing import Annotated, Any, NotRequired, TypedDict

from langchain.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt

from .attempts import AttemptService
from .engines import DecisionEngine, LangChainDecisionEngine, LazyLangChainDecisionEngine
from .message_content import normalize_message_content
from .schemas import AttemptDraft, PendingAction, Phase, ProblemMetadata, TurnDecision
from .services import MetadataResolver, PatternSweepService, StudyService


def _last_human_text(state: CoachState) -> str:
    last = next(
        (message for message in reversed(state.get("messages", [])) if isinstance(message, HumanMessage)),
        None,
    )
    return normalize_message_content(last.content).strip() if last else ""


def _routing_mode_command(text: str) -> str | None:
    """Recognize explicit workflow controls before model/bootstrap routing."""

    normalized = " ".join(text.lower().strip().split())
    if normalized in {"/auto", "/mode auto", "/退出扫荡"}:
        return "auto"
    mentions_sweep = "扫荡" in normalized or "pattern-sweep" in normalized or "pattern sweep" in normalized
    if mentions_sweep and any(token in normalized for token in ("退出", "关闭", "停止", "离开")):
        return "auto"
    if "自动选题" in normalized and any(token in normalized for token in ("切换", "进入", "恢复", "使用")):
        return "auto"
    if normalized in {"/sweep", "/mode pattern-sweep"}:
        return "pattern-sweep"
    if mentions_sweep and any(token in normalized for token in ("切换", "进入", "开启", "开始", "启用", "使用", "我要")):
        return "pattern-sweep"
    return None


def _next_subpattern_command(text: str) -> bool:
    normalized = " ".join(text.lower().strip().split())
    if normalized in {"/next-subpattern", "/next pattern"}:
        return True
    mentions_next = any(token in normalized for token in ("下一个", "继续下个", "next"))
    mentions_subpattern = any(token in normalized for token in ("小模式", "subpattern", "sub-pattern"))
    return mentions_next and mentions_subpattern


def _next_problem_command(text: str) -> bool:
    normalized = " ".join(text.lower().strip().split())
    return normalized in {"下一题", "继续下一题", "下道题", "next", "next problem", "/next"}


def _accepted_command(text: str) -> bool:
    normalized = " ".join(text.lower().strip().split())
    if any(token in normalized for token in (
        "没 ac", "没有 ac", "未 ac", "没过", "未通过", "not ac", "didn't get ac", "did not get ac",
    )):
        return False
    if normalized in {"/ac", "ac", "ac 了", "ac了", "提交通过", "提交通过了", "过了"}:
        return True
    if re.fullmatch(r"#?\d+\s*ac\s*(了|通过)?[。.!！]?", normalized):
        return True
    if re.search(r"\b(?:got|received|earned)\s+ac\b", normalized):
        return True
    if re.search(r"(?:\bno\.?\s*|\bnumber\s*|#)\d+.*\bac\b", normalized):
        return True
    return "ac" in normalized and any(token in normalized for token in ("通过了", "accepted"))


def _approval_chat_command(text: str) -> str | None:
    """Allow explicit HITL decisions when a chat UI hides interrupt controls."""

    normalized = " ".join(text.lower().strip().split())
    if normalized in {"批准", "同意", "确认", "approve", "/approve", "批准并继续"}:
        return "approve"
    if normalized in {"拒绝", "不同意", "reject", "/reject", "不要保存"}:
        return "reject"
    return None


def _has_recent_accepted_report(state: CoachState) -> bool:
    human_messages = (
        normalize_message_content(message.content)
        for message in state.get("messages", [])[-12:]
        if isinstance(message, HumanMessage)
    )
    return any(_accepted_command(text) for text in human_messages)


class CoachState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    phase: NotRequired[str]
    selected_problem: NotRequired[dict[str, Any] | None]
    routing_mode: NotRequired[str]
    training_mode: NotRequired[str]
    sweep_category: NotRequired[dict[str, Any] | None]
    sweep_subpattern: NotRequired[dict[str, Any] | None]
    sweep_card_category: NotRequired[str | None]
    hint_level: NotRequired[int]
    judge_result: NotRequired[str | None]
    judge_failures: NotRequired[list[str]]
    attempt_draft: NotRequired[dict[str, Any] | None]
    teach_back_assessment: NotRequired[dict[str, Any] | None]
    pending_action: NotRequired[dict[str, Any] | None]
    day_plan: NotRequired[dict[str, Any]]
    thread_id: NotRequired[str]
    last_error: NotRequired[str | None]
    archive_completed: NotRequired[bool]
    attempt_recorded: NotRequired[bool]
    assessment_requested: NotRequired[bool]


class TrainingGraph:
    def __init__(
        self,
        study: StudyService,
        sweep: PatternSweepService,
        resolver: MetadataResolver,
        engine: DecisionEngine,
        attempts: AttemptService | None = None,
    ):
        self.study, self.sweep, self.resolver, self.engine = study, sweep, resolver, engine
        self.attempts = attempts or AttemptService(study, sweep)

    def build(self, checkpointer: Any = None):
        graph = StateGraph(CoachState)
        graph.add_node("load_context", self.load_context)
        graph.add_node("select_next", self.select_next)
        graph.add_node("resolve_metadata", self.resolve_metadata)
        graph.add_node("choose_mode", self.choose_mode)
        graph.add_node("process_turn", self.process_turn)
        graph.add_node("recover_accepted", self.recover_accepted)
        graph.add_node("assess_teach_back", self.assess_teach_back)
        graph.add_node("prepare_persist", self.prepare_persist)
        graph.add_node("pending_notice", self.pending_notice)
        graph.add_node("chat_approval", self.chat_approval)
        graph.add_node("approval", self.approval)
        graph.add_node("persist", self.persist)
        graph.add_node("sync_sweep", self.sync_sweep)
        graph.add_node("session_summary", self.session_summary)

        graph.add_conditional_edges(START, self.route_start, {
            "load": "load_context", "turn": "process_turn", "recover": "recover_accepted",
            "assess": "assess_teach_back",
            "migrate": "prepare_persist",
            "pending": "pending_notice", "chat_approval": "chat_approval",
            "approval": "approval", "end": END,
        })
        graph.add_edge("load_context", "select_next")
        graph.add_conditional_edges("select_next", self.route_after_selection, {
            "card": END, "ready": "resolve_metadata", "end": END,
        })
        graph.add_conditional_edges("resolve_metadata", self.route_after_metadata, {
            "approval": "approval", "ready": "choose_mode", "end": END,
        })
        graph.add_edge("choose_mode", END)
        graph.add_conditional_edges("process_turn", self.route_after_turn, {
            "select": "select_next", "assess": "assess_teach_back",
            "persist": "prepare_persist", "end": END,
        })
        graph.add_edge("recover_accepted", "assess_teach_back")
        graph.add_conditional_edges("assess_teach_back", self.route_after_assessment, {
            "persist": "prepare_persist", "end": END,
        })
        graph.add_edge("prepare_persist", "approval")
        graph.add_edge("pending_notice", "approval")
        graph.add_conditional_edges("chat_approval", self.route_after_approval, {"persist": "persist", "sync": "sync_sweep", "ready": "choose_mode", "end": END})
        graph.add_conditional_edges("approval", self.route_after_approval, {"persist": "persist", "sync": "sync_sweep", "ready": "choose_mode", "end": END})
        graph.add_conditional_edges("persist", self.route_after_persist, {"prepare": "prepare_persist", "approval": "approval", "ready": "choose_mode", "end": END})
        graph.add_edge("sync_sweep", "session_summary")
        graph.add_edge("session_summary", END)
        return graph.compile(checkpointer=checkpointer)

    @staticmethod
    def route_start(state: CoachState) -> str:
        if state.get("pending_action"):
            pending = state.get("pending_action") or {}
            if pending.get("action") in {"finish_attempt", "archive_solution", "sync_pattern_sweep"}:
                # Collapse completion checkpoints created by the previous graph
                # into the new single preview/approval transaction.
                return "migrate"
            # A Command(resume=...) continues inside the interrupted approval
            # node and does not enter at START. Reaching START with a pending
            # action therefore means the UI submitted an ordinary chat message
            # instead of resolving the interrupt. Acknowledge it before
            # presenting the approval request again so the UI never appears
            # silent.
            return "chat_approval" if _approval_chat_command(_last_human_text(state)) else "pending"
        messages = state.get("messages", [])
        if messages and not isinstance(messages[-1], HumanMessage):
            # Resuming an idle checkpoint without a new learner message must
            # not replay the previous turn through the conversational agent.
            return "end"
        text = _last_human_text(state)
        if _routing_mode_command(text) is not None or _next_subpattern_command(text):
            return "turn"
        if _next_problem_command(text):
            return "load"
        if _accepted_command(text):
            return "turn"
        if not state.get("judge_result") and state.get("selected_problem") and _has_recent_accepted_report(state):
            return "recover"
        selected = state.get("selected_problem") or {}
        if state.get("routing_mode") == "pattern-sweep" and selected and selected.get("reason") != "pattern-sweep":
            return "load"
        if state.get("phase") == Phase.PATTERN_CARD and state.get("routing_mode") == "pattern-sweep":
            return "load"
        if state.get("phase") == Phase.COMPLETE:
            return "load" if _next_problem_command(text) else "turn"
        if not state.get("selected_problem"):
            return "turn" if messages else "load"
        return "turn"

    def load_context(self, state: CoachState) -> dict[str, Any]:
        return {
            "phase": Phase.LOADING.value,
            "day_plan": self.study.plan_day(),
            "routing_mode": state.get("routing_mode", "auto"),
            "selected_problem": None if state.get("routing_mode") == "pattern-sweep" else state.get("selected_problem"),
            "hint_level": 0,
            "last_error": None,
        }

    def select_next(self, state: CoachState) -> dict[str, Any]:
        if state.get("routing_mode") == "pattern-sweep":
            return self.select_next_sweep(state)
        status = self.study.status()
        due = status.get("due_reviews") or []
        selected = due[0] if due else self.study.in_progress_problem()
        if selected is None:
            sweep_item = self.sweep.recommend_next()
            selected = sweep_item.get("problem") if sweep_item else None
            if selected is not None:
                selected = {**selected, "reason": sweep_item.get("kind", "sweep"), "needs_mcp": sweep_item.get("needs_mcp", False)}
        if selected is None:
            selected = self.study.next_problem()
        if selected is None:
            return {"phase": Phase.COMPLETE.value, "messages": [AIMessage(content="当前没有可训练题目。")], "selected_problem": None}
        return {
            "phase": Phase.SELECTING.value,
            "selected_problem": selected,
            "attempt_draft": None,
            "teach_back_assessment": None,
            "attempt_recorded": False,
            "archive_completed": False,
            "judge_result": None,
            "judge_failures": [],
        }

    def select_next_sweep(self, state: CoachState) -> dict[str, Any]:
        item = self.sweep.recommend_next()
        if item is None:
            return {
                "phase": Phase.COMPLETE.value,
                "selected_problem": None,
                "messages": [AIMessage(content="题型扫荡 curriculum 已全部完成。")],
            }
        category = item["category"]
        subpattern = item["subpattern"]
        category_state = {"slug": category["slug"], "title": category["title"]}
        subpattern_state = {"slug": subpattern["slug"], "title": subpattern["title"]}
        if state.get("sweep_card_category") != category["slug"]:
            card = self.sweep.pattern_card(category["slug"])
            content = card["content"] if card else f"# {category['title']}\n\n模式卡内容尚未准备好。"
            subpatterns = "、".join(item["title"] for item in (card or {}).get("subpatterns", []))
            suffix = f"\n\n本 pattern 的小模式：{subpatterns}。" if subpatterns else ""
            return {
                "phase": Phase.PATTERN_CARD.value,
                "selected_problem": None,
                "sweep_category": category_state,
                "sweep_subpattern": subpattern_state,
                "sweep_card_category": category["slug"],
                "messages": [AIMessage(content=(
                    f"## 新 Pattern：{category['title']}\n\n{content}{suffix}\n\n"
                    "先阅读模式卡；准备好后回复“继续”，我会从第一个未完成的小模式开始。"
                ))],
            }
        selected = {
            **item["problem"],
            "reason": "pattern-sweep",
            "needs_mcp": item.get("needs_mcp", False),
            "pattern": category_state,
            "subpattern": subpattern_state,
        }
        return {
            "phase": Phase.SELECTING.value,
            "selected_problem": selected,
            "sweep_category": category_state,
            "sweep_subpattern": subpattern_state,
            "attempt_draft": None,
            "teach_back_assessment": None,
            "attempt_recorded": False,
            "archive_completed": False,
            "judge_result": None,
            "judge_failures": [],
        }

    @staticmethod
    def route_after_selection(state: CoachState) -> str:
        if state.get("phase") == Phase.PATTERN_CARD:
            return "card"
        if state.get("phase") == Phase.COMPLETE:
            return "end"
        return "ready"

    async def resolve_metadata(self, state: CoachState) -> dict[str, Any]:
        selected = state.get("selected_problem") or {}
        slug = selected.get("slug")
        if not slug:
            return {"phase": Phase.COMPLETE.value, "last_error": "Selected problem has no slug", "messages": [AIMessage(content="推荐题目缺少 slug，无法继续。")]}
        if await asyncio.to_thread(self.study.problem_context, slug):
            return {"phase": Phase.RESOLVING_METADATA.value}
        metadata = await self.resolver.resolve(slug)
        if metadata is None:
            return {
                "phase": Phase.COMPLETE.value,
                "last_error": "metadata_required",
                "messages": [AIMessage(content=f"题目 `{slug}` 缺少可靠 metadata。请配置 LeetCode MCP 或先用 CLI 初始化题目。")],
            }
        pending = PendingAction(
            action="initialize_problem",
            arguments=metadata.model_dump(),
            description=f"初始化题目 #{metadata.id} {metadata.title}",
        )
        return {"phase": Phase.AWAITING_APPROVAL.value, "pending_action": pending.model_dump()}

    @staticmethod
    def route_after_metadata(state: CoachState) -> str:
        if state.get("pending_action"):
            return "approval"
        return "end" if state.get("phase") == Phase.COMPLETE else "ready"

    def choose_mode(self, state: CoachState) -> dict[str, Any]:
        selected = state.get("selected_problem") or {}
        if selected.get("reason") == "due-review" or selected.get("status") in {"AC", "Review"}:
            mode = "redo-from-memory"
        elif state.get("routing_mode") == "pattern-sweep":
            mode = "pattern-contrast"
        else:
            mode = "guided-solve"
        title = selected.get("title") or selected.get("slug")
        sweep_prefix = ""
        if state.get("routing_mode") == "pattern-sweep":
            category = selected.get("pattern", {}).get("title", "")
            subpattern = selected.get("subpattern", {}).get("title", "")
            sweep_prefix = f"题型扫荡：{category} → 小模式：{subpattern}。\n\n"
        return {
            "phase": Phase.COACHING.value,
            "training_mode": mode,
            "messages": [AIMessage(content=(
                f"{sweep_prefix}本轮新题：{title}，训练模式：`{mode}`。"
                "先用自己的话说明题意和最直接的暴力解法。"
            ))],
        }

    def process_turn(self, state: CoachState) -> dict[str, Any]:
        text = _last_human_text(state)
        requested_mode = _routing_mode_command(text)
        if requested_mode is not None:
            label = "题型扫荡" if requested_mode == "pattern-sweep" else "自动选题"
            decision = TurnDecision(
                action="switch_mode",
                requested_mode=requested_mode,
                response=f"正在切换到{label}模式。",
            )
        elif _next_subpattern_command(text):
            if self._can_advance_subpattern(state):
                return {
                    "phase": Phase.SELECTING.value,
                    "selected_problem": None,
                    "messages": [AIMessage(content="当前训练证据已持久化，正在进入下一个小模式。")],
                }
            return {
                "phase": Phase.TEACH_BACK.value if state.get("judge_result") == "AC" else state.get("phase", Phase.COACHING.value),
                "messages": [AIMessage(content=(
                    "还不能进入下一个小模式：当前题目的完整 teach-back、写入审批和 pattern sweep 同步"
                    "尚未全部完成。先完成当前状态机步骤。"
                ))],
                "last_error": "subpattern_advance_guard",
            }
        elif text == "/quit":
            decision = TurnDecision(action="quit", response="已保存当前对话 checkpoint，下次可用同一 thread 继续。")
        elif _accepted_command(text):
            decision = TurnDecision(action="accepted", response="收到 AC。请完成 teach-back：说明 invariant、复杂度、最容易遗漏的边界，以及何时不适用。")
        else:
            decision = self.engine.decide(state)
        updates: dict[str, Any] = {"messages": [AIMessage(content=decision.response)]}
        phase = str(state.get("phase", Phase.COACHING.value))
        if decision.action in {"continue", "hint"}:
            updates["phase"] = phase if phase == Phase.TEACH_BACK.value else (
                Phase.DEBUGGING.value if phase == Phase.DEBUGGING.value else Phase.COACHING.value
            )
            updates["hint_level"] = min(4, int(state.get("hint_level", 0)) + (1 if decision.action == "hint" else 0))
        elif decision.action == "judge_failed":
            failure = (decision.judge_failure or "WA").upper()
            failures = list(state.get("judge_failures") or [])
            if failure not in failures:
                failures.append(failure)
            updates.update(
                phase=Phase.DEBUGGING.value,
                judge_result=failure,
                judge_failures=failures,
            )
        elif decision.action == "accepted":
            updates.update(phase=Phase.TEACH_BACK.value, judge_result="AC", assessment_requested=False)
        elif decision.action == "teach_back":
            if state.get("judge_result") != "AC":
                updates.update(
                    phase=phase,
                    messages=[AIMessage(content="我可以评估这段总结，但需要先确认本题已有 AC 判题结果。")],
                    last_error="teach_back_before_ac",
                )
            else:
                updates.update(phase=Phase.TEACH_BACK.value, assessment_requested=True, last_error=None)
        elif decision.action == "select_next":
            updates.update(
                phase=Phase.SELECTING.value,
                selected_problem=None,
                training_mode=None,
                hint_level=0,
                judge_result=None,
                judge_failures=[],
                attempt_draft=None,
                teach_back_assessment=None,
                attempt_recorded=False,
                archive_completed=False,
                assessment_requested=False,
                last_error=None,
            )
        elif decision.action == "switch_mode":
            requested_mode = decision.requested_mode
            if requested_mode is None:
                updates.update(
                    phase=state.get("phase", Phase.COACHING.value),
                    messages=[AIMessage(content="模式切换请求缺少目标模式，当前模式未改变。")],
                )
            else:
                label = "题型扫荡" if requested_mode == "pattern-sweep" else "自动选题"
                updates.update(
                    phase=Phase.SELECTING.value,
                    routing_mode=requested_mode,
                    selected_problem=None,
                    training_mode=None,
                    hint_level=0,
                    judge_result=None,
                    judge_failures=[],
                    attempt_draft=None,
                    teach_back_assessment=None,
                    attempt_recorded=False,
                    archive_completed=False,
                    assessment_requested=False,
                    sweep_category=None,
                    sweep_subpattern=None,
                    sweep_card_category=None,
                    messages=[AIMessage(content=f"已切换到{label}模式，正在按路由规则选择下一题。")],
                )
        elif decision.action == "quit":
            updates["phase"] = Phase.COMPLETE.value
        return updates

    def assess_teach_back(self, state: CoachState) -> dict[str, Any]:
        decision = self.engine.assess_teach_back(state)
        assessment = decision.assessment
        return {
            "phase": Phase.PERSISTING.value if assessment.complete else Phase.TEACH_BACK.value,
            "teach_back_assessment": assessment.model_dump(),
            "assessment_requested": False,
            "messages": [AIMessage(content=decision.response)],
            "last_error": None,
        }

    @staticmethod
    def recover_accepted(state: CoachState) -> dict[str, Any]:
        return {
            "phase": Phase.TEACH_BACK.value,
            "judge_result": "AC",
            "messages": [AIMessage(content="已从近期对话恢复遗漏的 AC 判题事件，正在重新评估 teach-back。")],
            "last_error": None,
        }

    @staticmethod
    def route_after_assessment(state: CoachState) -> str:
        return "persist" if state.get("phase") == Phase.PERSISTING else "end"

    @staticmethod
    def _can_advance_subpattern(state: CoachState) -> bool:
        assessment = state.get("teach_back_assessment") or {}
        assessment_complete = all((
            assessment.get("invariant_correct"),
            assessment.get("complexity_correct"),
            assessment.get("edge_case_identified"),
            assessment.get("pattern_boundary_understood"),
        ))
        return bool(assessment_complete and state.get("attempt_recorded") and not state.get("pending_action"))

    @staticmethod
    def route_after_turn(state: CoachState) -> str:
        if state.get("phase") == Phase.SELECTING and not state.get("selected_problem"):
            return "select"
        if state.get("assessment_requested"):
            return "assess"
        return "persist" if state.get("phase") == Phase.PERSISTING else "end"

    def prepare_persist(self, state: CoachState) -> dict[str, Any]:
        problem = state.get("selected_problem") or {}
        if not problem.get("slug"):
            return {
                "phase": Phase.COACHING.value,
                "pending_action": None,
                "last_error": "completion_without_problem",
                "messages": [AIMessage(content="当前没有可完成的题目，训练数据未改变。")],
            }
        assessment = state.get("teach_back_assessment") or {}
        quality = int(assessment.get("suggested_quality", 3))
        mastery = "solid" if quality == 5 and all((
            assessment.get("invariant_correct"), assessment.get("complexity_correct"),
            assessment.get("edge_case_identified"), assessment.get("pattern_boundary_understood"),
        )) else ("ok" if quality >= 3 else "shaky")
        judge_failures = list(state.get("judge_failures") or [])
        attempt = AttemptDraft(
            slug=problem["slug"], mastery=mastery, mode=state.get("training_mode", "guided-solve"),
            quality=quality, hint_level=int(state.get("hint_level", 0)),
            first_try_ac=not judge_failures,
            judge_failures=judge_failures,
            teach_back=True,
        )
        should_archive = bool(not state.get("archive_completed") and self.study.plugin_files(problem["slug"]))
        operations = ["更新题目训练记录", "同步 pattern sweep coverage", "写入 session log"]
        if should_archive:
            operations.insert(0, "归档 VS Code accepted solution")
        pending = PendingAction(
            action="complete_attempt",
            arguments={
                "attempt": attempt.model_dump(),
                "archive_solution": should_archive,
                "sync_pattern_sweep": True,
                "log_session": True,
            },
            description=f"完成 {attempt.slug}：" + "、".join(operations),
        )
        return {
            "phase": Phase.AWAITING_APPROVAL.value,
            "attempt_draft": attempt.model_dump(),
            "pending_action": pending.model_dump(),
            "messages": [AIMessage(content=(
                "训练已达到可持久化条件。以下变更将作为一次完整操作执行：\n- "
                + "\n- ".join(operations)
                + "\n批准前不会修改学习数据。"
            ))],
            "last_error": None,
        }

    @staticmethod
    def pending_notice(state: CoachState) -> dict[str, Any]:
        pending = state.get("pending_action") or {}
        description = pending.get("description") or pending.get("action") or "当前写入"
        return {
            "phase": Phase.AWAITING_APPROVAL.value,
            "messages": [AIMessage(content=(
                f"已收到你的消息，但还不能进入下一题：正在等待你审批“{description}”。"
                "请先选择 approve、edit 或 reject；学习数据在批准前不会改变。"
            ))],
            "last_error": "approval_required",
        }

    @staticmethod
    def chat_approval(state: CoachState) -> dict[str, Any]:
        pending = state.get("pending_action") or {}
        decision = _approval_chat_command(_last_human_text(state))
        if decision == "approve":
            return {
                "phase": Phase.PERSISTING.value,
                "messages": [AIMessage(content=f"已批准：{pending.get('description') or pending.get('action')}。")],
                "last_error": None,
            }
        is_init = pending.get("action") == "initialize_problem"
        return {
            "pending_action": None,
            "phase": Phase.COMPLETE.value if is_init else Phase.COACHING.value,
            "messages": [AIMessage(content="已拒绝写入；学习数据未改变。")],
            "last_error": None,
        }

    def approval(self, state: CoachState) -> dict[str, Any]:
        pending = state.get("pending_action")
        if not pending:
            return {"phase": Phase.COACHING.value}
        response = interrupt(pending)
        decision = response.get("type", "reject") if isinstance(response, dict) else str(response)
        if decision == "edit" and isinstance(response, dict) and isinstance(response.get("arguments"), dict):
            pending = {**pending, "arguments": response["arguments"]}
            if pending["action"] == "finish_attempt":
                AttemptDraft.model_validate(pending["arguments"])
            elif pending["action"] == "complete_attempt":
                AttemptDraft.model_validate(pending["arguments"].get("attempt"))
            elif pending["action"] == "initialize_problem":
                ProblemMetadata.model_validate(pending["arguments"])
            return {"pending_action": pending, "phase": Phase.PERSISTING.value}
        if decision == "approve":
            return {"phase": Phase.PERSISTING.value}
        is_init = pending.get("action") == "initialize_problem"
        return {
            "pending_action": None,
            "phase": Phase.COMPLETE.value if is_init else Phase.COACHING.value,
            "messages": [AIMessage(content="已拒绝写入；学习数据未改变。")],
        }

    @staticmethod
    def route_after_approval(state: CoachState) -> str:
        if state.get("phase") == Phase.PERSISTING:
            pending = state.get("pending_action") or {}
            return "sync" if pending.get("action") == "sync_pattern_sweep" else "persist"
        return "end" if state.get("phase") == Phase.COMPLETE else "ready"

    def persist(self, state: CoachState) -> dict[str, Any]:
        pending = state.get("pending_action") or {}
        try:
            if pending.get("action") == "initialize_problem":
                self.study.initialize_problem(ProblemMetadata.model_validate(pending["arguments"]))
                return {"pending_action": None, "phase": Phase.SELECTING.value, "messages": [AIMessage(content="题目已初始化。")], "last_error": None}
            if pending.get("action") == "complete_attempt":
                arguments = pending["arguments"]
                attempt = AttemptDraft.model_validate(arguments.get("attempt"))
                result = self.attempts.complete(
                    attempt,
                    archive_solution=bool(arguments.get("archive_solution")),
                    sync_pattern_sweep=bool(arguments.get("sync_pattern_sweep", True)),
                    log_session=bool(arguments.get("log_session", True)),
                )
                return {
                    "pending_action": None,
                    "phase": Phase.COMPLETE.value,
                    "attempt_recorded": result.attempt_recorded,
                    "archive_completed": result.archive_completed or state.get("archive_completed", False),
                    "last_error": None,
                    "messages": [AIMessage(content="训练记录、solution 归档（如适用）、pattern sweep 和 session 已一次完成。可以进入下一题。")],
                }
            if pending.get("action") == "finish_attempt":
                self.study.finish_attempt(AttemptDraft.model_validate(pending["arguments"]))
                sync = PendingAction(action="sync_pattern_sweep", arguments={}, description="同步 pattern sweep coverage 和受控 sweep-map 区域")
                return {"pending_action": sync.model_dump(), "phase": Phase.AWAITING_APPROVAL.value, "attempt_recorded": True, "last_error": None}
            if pending.get("action") == "archive_solution":
                self.study.archive_solution(pending["arguments"]["slug"], pending["arguments"].get("source"))
                return {"pending_action": None, "phase": Phase.PERSISTING.value, "archive_completed": True, "last_error": None}
            raise ValueError(f"Unsupported pending action: {pending.get('action')}")
        except Exception as exc:
            return {"phase": Phase.COACHING.value, "pending_action": None, "last_error": str(exc), "messages": [AIMessage(content=f"写入失败：{exc}")]}

    @staticmethod
    def route_after_persist(state: CoachState) -> str:
        if not state.get("last_error") and state.get("phase") == Phase.SELECTING:
            return "ready"
        if not state.get("last_error") and state.get("phase") == Phase.AWAITING_APPROVAL:
            return "approval"
        if not state.get("last_error") and state.get("archive_completed") and not state.get("attempt_draft"):
            return "prepare"
        return "end"

    def sync_sweep(self, state: CoachState) -> dict[str, Any]:
        self.sweep.sync()
        return {"phase": Phase.PERSISTING.value, "pending_action": None}

    def session_summary(self, state: CoachState) -> dict[str, Any]:
        problem = state.get("selected_problem") or {}
        draft = state.get("attempt_draft") or {}
        self.study.log_session(
            problems=[problem.get("slug", "")], summary="完成 AC 与 teach-back",
            next_step="按 next_review 复习", mode=state.get("training_mode", "guided-solve"), quality=int(draft.get("quality", 3)),
        )
        return {"phase": Phase.COMPLETE.value, "messages": [AIMessage(content="训练记录和 pattern sweep 已同步。本轮完成。")], "pending_action": None}


__all__ = [
    "CoachState", "DecisionEngine", "LangChainDecisionEngine",
    "LazyLangChainDecisionEngine", "TrainingGraph", "Command",
]
