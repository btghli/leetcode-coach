"""The explicit LangGraph training lifecycle around a LangChain coaching agent."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any, NotRequired, TypedDict

from langchain.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt

from .attempts import AttemptService
from .chat_commands import (
    accepted_command,
    approval_command,
    next_problem_command,
    next_subpattern_command,
    routing_mode_command,
)
from .engines import DecisionEngine, LangChainDecisionEngine, LazyLangChainDecisionEngine
from .message_content import normalize_message_content
from .schemas import AttemptDraft, PendingAction, Phase, ProblemMetadata, TeachBackAssessment, TurnDecision
from .services import MetadataResolver, PatternSweepService, StudyService


CANONICAL_PENDING_ACTIONS = frozenset({"initialize_problem", "complete_attempt"})
TEACH_BACK_START_MESSAGE = (
    "收到 AC。我们一次只复盘一点：你的核心数据结构（例如 map、stack 或 queue）里保存的内容代表什么？"
    "试着补一句“它保存____，因此我能____”。想不起来可以点“复盘提示”。"
)


def _last_human_text(state: CoachState) -> str:
    last = next(
        (message for message in reversed(state.get("messages", [])) if isinstance(message, HumanMessage)),
        None,
    )
    return normalize_message_content(last.content).strip() if last else ""


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
    thread_id: NotRequired[str]
    last_error: NotRequired[str | None]
    archive_completed: NotRequired[bool]
    attempt_recorded: NotRequired[bool]
    teach_back_start_index: NotRequired[int | None]
    skip_problem_slug: NotRequired[str | None]
    workflow_command: NotRequired[str | None]
    workflow_value: NotRequired[str | None]


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
        graph.add_node("prepare_persist", self.prepare_persist)
        graph.add_node("pending_notice", self.pending_notice)
        graph.add_node("chat_approval", self.chat_approval)
        graph.add_node("approval", self.approval)
        graph.add_node("persist", self.persist)

        graph.add_conditional_edges(START, self.route_start, {
            "load": "load_context", "turn": "process_turn",
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
            "select": "select_next", "persist": "prepare_persist", "end": END,
        })
        graph.add_edge("prepare_persist", "approval")
        graph.add_edge("pending_notice", "approval")
        graph.add_conditional_edges("chat_approval", self.route_after_approval, {"approval": "approval", "persist": "persist", "ready": "choose_mode", "end": END})
        graph.add_conditional_edges("approval", self.route_after_approval, {"approval": "approval", "persist": "persist", "ready": "choose_mode", "end": END})
        graph.add_conditional_edges("persist", self.route_after_persist, {"ready": "choose_mode", "end": END})
        from .observability import trace_config
        return graph.compile(checkpointer=checkpointer).with_config(trace_config(self.study.root))

    @staticmethod
    def route_start(state: CoachState) -> str:
        if state.get("pending_action"):
            pending = state.get("pending_action") or {}
            if pending.get("action") not in CANONICAL_PENDING_ACTIONS:
                # Collapse completion checkpoints created by the previous graph
                # into the new single preview/approval transaction.
                return "migrate"
            # A Command(resume=...) continues inside the interrupted approval
            # node and does not enter at START. Reaching START with a pending
            # action therefore means the UI submitted an ordinary chat message
            # instead of resolving the interrupt. Acknowledge it before
            # presenting the approval request again so the UI never appears
            # silent.
            return "chat_approval" if approval_command(_last_human_text(state)) else "pending"
        if (state.get("workflow_command") == "next_problem"
                and state.get("judge_result") == "AC"
                and not state.get("attempt_recorded")):
            return "turn"
        if state.get("workflow_command") == "next_problem":
            return "load"
        if state.get("workflow_command") == "judge_result":
            return "turn"
        messages = state.get("messages", [])
        if messages and not isinstance(messages[-1], HumanMessage):
            # Resuming an idle checkpoint without a new learner message must
            # not replay the previous turn through the conversational agent.
            return "end"
        text = _last_human_text(state)
        if next_problem_command(text) and state.get("judge_result") == "AC" and not state.get("attempt_recorded"):
            return "turn"
        if routing_mode_command(text) is not None or next_subpattern_command(text):
            return "turn"
        if next_problem_command(text):
            return "load"
        if accepted_command(text):
            return "turn"
        selected = state.get("selected_problem") or {}
        if state.get("routing_mode") == "pattern-sweep" and selected and selected.get("reason") != "pattern-sweep":
            return "load"
        if state.get("phase") == Phase.PATTERN_CARD and state.get("routing_mode") == "pattern-sweep":
            return "load"
        if state.get("phase") == Phase.COMPLETE:
            return "load" if next_problem_command(text) else "turn"
        if not state.get("selected_problem"):
            return "turn" if messages else "load"
        return "turn"

    def load_context(self, state: CoachState) -> dict[str, Any]:
        selected = state.get("selected_problem") or {}
        advances = state.get("workflow_command") == "next_problem" or next_problem_command(_last_human_text(state))
        skip_slug = selected.get("slug") if advances else None
        return {
            "phase": Phase.LOADING.value,
            "routing_mode": state.get("routing_mode", "auto"),
            "selected_problem": None if state.get("routing_mode") == "pattern-sweep" else state.get("selected_problem"),
            "hint_level": 0,
            "skip_problem_slug": skip_slug,
            "workflow_command": None,
            "workflow_value": None,
            "last_error": None,
        }

    def select_next(self, state: CoachState) -> dict[str, Any]:
        if state.get("routing_mode") == "pattern-sweep":
            return self.select_next_sweep(state)
        # Normal routing has one deterministic owner. Pattern curriculum is a
        # separate lane selected explicitly above.
        selected = self.study.next_problem(exclude_slug=state.get("skip_problem_slug"))
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
            "teach_back_start_index": None,
            "skip_problem_slug": None,
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
            "teach_back_start_index": None,
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
        opening = {
            "redo-from-memory": "直接复盘核心分组 key、一次遍历如何更新数据结构，以及复杂度。",
            "pattern-contrast": "先说明这个小模式的识别信号，以及它和相近模式最关键的区别。",
            "blind-solve": "先独立说明思路和关键不变量，再开始实现。",
            "debug-drill": "先给出最小失败输入和实际输出，再定位第一个错误状态。",
        }.get(mode, "先用自己的话说明题意和思路；如果已经知道优化解法，可以直接说明。")
        return {
            "phase": Phase.COACHING.value,
            "training_mode": mode,
            "messages": [AIMessage(content=(
                f"{sweep_prefix}本轮新题：{title}，训练模式：`{mode}`。"
                f"{opening}"
            ))],
        }

    def process_turn(self, state: CoachState) -> dict[str, Any]:
        text = _last_human_text(state)
        requested_mode = routing_mode_command(text)
        workflow_command = state.get("workflow_command")
        workflow_value = str(state.get("workflow_value") or "").upper()
        wants_next = workflow_command == "next_problem" or next_problem_command(text)
        if wants_next and state.get("judge_result") == "AC" and not state.get("attempt_recorded"):
            return {
                "phase": Phase.TEACH_BACK.value,
                "workflow_command": None,
                "workflow_value": None,
                "messages": [AIMessage(content="本题 AC 尚未保存。先完成简短复盘并批准写入，再进入下一题。")],
                "last_error": "completion_required",
            }
        if workflow_command == "judge_result" and workflow_value == "AC":
            decision = TurnDecision(action="accepted", response=TEACH_BACK_START_MESSAGE)
        elif workflow_command == "judge_result" and workflow_value in {"WA", "TLE", "RE", "MLE"}:
            decision = TurnDecision(
                action="judge_failed",
                judge_failure=workflow_value,
                response=f"收到 {workflow_value}。请贴出最小失败输入、实际输出或完整报错。",
            )
        elif requested_mode is not None:
            label = "题型扫荡" if requested_mode == "pattern-sweep" else "自动选题"
            decision = TurnDecision(
                action="switch_mode",
                requested_mode=requested_mode,
                response=f"正在切换到{label}模式。",
            )
        elif next_subpattern_command(text):
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
        elif accepted_command(text):
            decision = TurnDecision(action="accepted", response=TEACH_BACK_START_MESSAGE)
        elif state.get("phase") == Phase.TEACH_BACK.value and state.get("judge_result") == "AC":
            teach_back = self.engine.assess_teach_back(state)
            if teach_back.action == "continue":
                return {
                    "phase": Phase.TEACH_BACK.value,
                    "messages": [AIMessage(content=teach_back.response)],
                    "last_error": None,
                }
            assessment = teach_back.assessment
            return {
                "phase": Phase.PERSISTING.value if assessment.complete else Phase.TEACH_BACK.value,
                "teach_back_assessment": assessment.model_dump(),
                "messages": [AIMessage(content=teach_back.response)],
                "last_error": None,
            }
        else:
            decision = self.engine.decide(state)
        updates: dict[str, Any] = {
            "messages": [AIMessage(content=decision.response)],
            "workflow_command": None,
            "workflow_value": None,
        }
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
            updates.update(
                phase=Phase.TEACH_BACK.value,
                judge_result="AC",
                teach_back_start_index=len(state.get("messages", [])),
            )
        elif decision.action == "select_next":
            current = state.get("selected_problem") or {}
            updates.update(
                phase=Phase.SELECTING.value,
                selected_problem=None,
                skip_problem_slug=current.get("slug"),
                training_mode=None,
                hint_level=0,
                judge_result=None,
                judge_failures=[],
                attempt_draft=None,
                teach_back_assessment=None,
                attempt_recorded=False,
                archive_completed=False,
                teach_back_start_index=None,
                last_error=None,
                messages=[AIMessage(content="正在按确定性学习计划选择下一题。")],
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
                    teach_back_start_index=None,
                    sweep_category=None,
                    sweep_subpattern=None,
                    sweep_card_category=None,
                    messages=[AIMessage(content=f"已切换到{label}模式，正在按路由规则选择下一题。")],
                )
        elif decision.action == "quit":
            updates["phase"] = Phase.COMPLETE.value
        return updates

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
        judge_failures = list(state.get("judge_failures") or [])
        preview = self.attempts.prepare(
            slug=problem["slug"],
            training_mode=state.get("training_mode", "guided-solve"),
            assessment=TeachBackAssessment.model_validate(state.get("teach_back_assessment") or {}),
            hint_level=int(state.get("hint_level", 0)),
            judge_failures=judge_failures,
            archive_completed=bool(state.get("archive_completed")),
        )
        return {
            "phase": Phase.AWAITING_APPROVAL.value,
            "attempt_draft": preview.attempt.model_dump(),
            "pending_action": preview.pending_action.model_dump(),
            "messages": [AIMessage(content=(
                "训练已达到可持久化条件。以下变更将作为一次完整操作执行：\n- "
                + "\n- ".join(preview.operations)
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

    def chat_approval(self, state: CoachState) -> dict[str, Any]:
        decision = approval_command(_last_human_text(state))
        return self._resolve_approval(state, {"type": decision or "reject"}, announce=True)

    def approval(self, state: CoachState) -> dict[str, Any]:
        pending = state.get("pending_action")
        if not pending:
            return {"phase": Phase.COACHING.value}
        response = interrupt(pending)
        return self._resolve_approval(state, response)

    def _resolve_approval(
        self,
        state: CoachState,
        response: Any,
        *,
        announce: bool = False,
    ) -> dict[str, Any]:
        """Apply one approval response for chat and interrupt entry points."""

        pending = state.get("pending_action") or {}
        decision = response.get("type", "reject") if isinstance(response, dict) else str(response)
        if decision in {"approve", "edit"} and pending.get("action") not in CANONICAL_PENDING_ACTIONS:
            # Old checkpoints may contain one of the former multi-step writes.
            # Replace it with the grouped preview and require fresh approval.
            return self.prepare_persist(state)
        if decision == "edit" and isinstance(response, dict) and isinstance(response.get("arguments"), dict):
            pending = {**pending, "arguments": response["arguments"]}
            if pending["action"] == "complete_attempt":
                AttemptDraft.model_validate(pending["arguments"].get("attempt"))
            elif pending["action"] == "initialize_problem":
                ProblemMetadata.model_validate(pending["arguments"])
            return {"pending_action": pending, "phase": Phase.PERSISTING.value}
        if decision == "approve":
            updates: dict[str, Any] = {"phase": Phase.PERSISTING.value, "last_error": None}
            if announce:
                updates["messages"] = [AIMessage(content=f"已批准：{pending.get('description') or pending.get('action')}。")]
            return updates
        is_init = pending.get("action") == "initialize_problem"
        return {
            "pending_action": None,
            "phase": Phase.COMPLETE.value if is_init else Phase.COACHING.value,
            "messages": [AIMessage(content="已拒绝写入；学习数据未改变。")],
            "last_error": None,
        }

    @staticmethod
    def route_after_approval(state: CoachState) -> str:
        if state.get("phase") == Phase.AWAITING_APPROVAL:
            return "approval"
        if state.get("phase") == Phase.PERSISTING:
            return "persist"
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
                # Recompute from the deterministic scheduler only after the
                # grouped write succeeds. This lets the coach hand off the
                # next activity without creating a competing lesson record.
                next_plan = self.study.plan_day()
                next_item = next_plan.get("recommended_next") or {}
                next_title = next_item.get("title") or next_item.get("slug")
                handoff = (
                    f"下一步建议：{next_title}（{next_plan.get('suggested_mode', 'guided-solve')}）。"
                    if next_title else "今天没有其他待安排的题目。"
                )
                return {
                    "pending_action": None,
                    "phase": Phase.COMPLETE.value,
                    "attempt_recorded": result.attempt_recorded,
                    "archive_completed": result.archive_completed or state.get("archive_completed", False),
                    "last_error": None,
                    "messages": [AIMessage(content=(
                        "训练记录、solution 归档（如适用）、pattern sweep 和 session 已一次完成。"
                        + handoff + "准备好后点击“下一题”或发送“下一题”。"
                    ))],
                }
            raise ValueError(f"Unsupported pending action: {pending.get('action')}")
        except Exception as exc:
            return {"phase": Phase.COACHING.value, "pending_action": None, "last_error": str(exc), "messages": [AIMessage(content=f"写入失败：{exc}")]}

    @staticmethod
    def route_after_persist(state: CoachState) -> str:
        if not state.get("last_error") and state.get("phase") == Phase.SELECTING:
            return "ready"
        return "end"


__all__ = [
    "CoachState", "DecisionEngine", "LangChainDecisionEngine",
    "LazyLangChainDecisionEngine", "TrainingGraph", "Command",
]
