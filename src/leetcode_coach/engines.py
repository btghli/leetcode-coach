"""Bounded decision-engine adapters used by the LangGraph workflow."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, TypeVar

from pydantic import BaseModel

from langchain.agents import create_agent
from langchain.messages import HumanMessage

from .config import AppConfig, initialize_model
from .message_content import normalize_message_content
from .prompts import COACH_SYSTEM_PROMPT
from .schemas import DecisionContext, Phase, TeachBackAssessment, TeachBackDecision, TurnDecision
from .services import PatternSweepService, StudyService
from .tools import build_read_tools


class DecisionEngine(Protocol):
    def decide(self, state: Mapping[str, Any]) -> TurnDecision: ...

    def assess_teach_back(self, state: Mapping[str, Any]) -> TeachBackDecision: ...


class LangChainDecisionEngine:
    def __init__(self, model: Any, study: StudyService, sweep: PatternSweepService):
        tools = build_read_tools(study, sweep)
        self.agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=COACH_SYSTEM_PROMPT,
            response_format=TurnDecision,
        )
        self.teach_back_agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=(
                f"{COACH_SYSTEM_PROMPT}\n\n"
                "You are only evaluating the cumulative teach-back after an accepted solution. "
                "Return TeachBackDecision. Set each assessment boolean independently from evidence in the learner's "
                "messages. The workflow derives completion from those booleans; response prose cannot complete it."
            ),
            response_format=TeachBackDecision,
        )

    def decide(self, state: Mapping[str, Any]) -> TurnDecision:
        problem = state.get("selected_problem") or {}
        phase = state.get("phase", Phase.COACHING)
        context = HumanMessage(content=(
            "Workflow context (authoritative): "
            f"phase={phase}; problem={problem.get('slug')}; routing_mode={state.get('routing_mode', 'auto')}; "
            f"training_mode={state.get('training_mode')}; "
            f"hint_level={state.get('hint_level', 0)}. Interpret the latest learner message and choose the next action."
        ))
        result = self.agent.invoke({"messages": [*state.get("messages", []), context]})
        structured = result.get("structured_response")
        return structured if isinstance(structured, TurnDecision) else TurnDecision.model_validate(structured)

    def assess_teach_back(self, state: Mapping[str, Any]) -> TeachBackDecision:
        problem = state.get("selected_problem") or {}
        context = HumanMessage(content=(
            "Workflow context (authoritative): "
            f"phase=teach_back; problem={problem.get('slug')}; judge_result={state.get('judge_result')}. "
            "Evaluate invariant, complexity, a valid edge case, and the boundary where this pattern does not apply."
        ))
        result = self.teach_back_agent.invoke({"messages": [*state.get("messages", []), context]})
        structured = result.get("structured_response")
        return structured if isinstance(structured, TeachBackDecision) else TeachBackDecision.model_validate(structured)


class LazyLangChainDecisionEngine:
    """Delay provider initialization until a learner message actually needs the LLM."""

    def __init__(self, model_name: str | None, study: StudyService, sweep: PatternSweepService):
        self.model_name, self.study, self.sweep = model_name, study, sweep
        self._delegate: LangChainDecisionEngine | None = None

    def decide(self, state: Mapping[str, Any]) -> TurnDecision:
        error = self._ensure_delegate()
        if error:
            return TurnDecision(action="continue", response=error)
        try:
            assert self._delegate is not None
            return self._delegate.decide(state)
        except Exception as exc:
            code = getattr(exc, "code", None)
            if code == "insufficient_quota" or "insufficient_quota" in str(exc):
                return TurnDecision(
                    action="continue",
                    response=(
                        "OpenAI API key 已通过认证，但当前项目没有可用额度。"
                        "请在 https://platform.openai.com/settings/organization/billing 配置 API billing 后重试。"
                    ),
                )
            raise

    def assess_teach_back(self, state: Mapping[str, Any]) -> TeachBackDecision:
        error = self._ensure_delegate()
        if error:
            return _failed_teach_back(error)
        try:
            assert self._delegate is not None
            return self._delegate.assess_teach_back(state)
        except Exception as exc:
            code = getattr(exc, "code", None)
            if code == "insufficient_quota" or "insufficient_quota" in str(exc):
                return _failed_teach_back(
                    "OpenAI API key 已通过认证，但当前项目没有可用额度；teach-back 状态未改变。"
                )
            raise

    def _ensure_delegate(self) -> str | None:
        if self._delegate is not None:
            return None
        try:
            model = initialize_model(self.model_name)
        except ValueError as exc:
            return f"模型尚未配置：{exc} 设置后重启 Agent Server 即可继续。"
        self._delegate = LangChainDecisionEngine(model, self.study, self.sweep)
        return None


CompletedProcessRunner = Callable[..., subprocess.CompletedProcess[str]]
MAX_MESSAGE_CHARS = 4_000
MAX_NOTE_CHARS = 12_000


def find_codex_executable(explicit: str | None = None) -> str | None:
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.is_file():
            return str(candidate)
        return shutil.which(explicit)
    discovered = shutil.which("codex")
    if discovered:
        return discovered
    names = ("codex.exe", "codex") if shutil.which("cmd") else ("codex",)
    candidates: list[Path] = []
    for name in names:
        candidates.extend(Path.home().glob(f".vscode/extensions/openai.chatgpt-*/bin/*/{name}"))
    files = [path for path in candidates if path.is_file()]
    return str(max(files, key=lambda path: path.stat().st_mtime)) if files else None


def _message_content(message: Any) -> str:
    rendered = normalize_message_content(getattr(message, "content", ""))
    return rendered if len(rendered) <= MAX_MESSAGE_CHARS else f"{rendered[:MAX_MESSAGE_CHARS]}\n[truncated]"


def build_study_summary(study: StudyService) -> dict[str, Any]:
    """Expose compact aggregate facts without handing the agent repository access."""

    status = study.status()
    plan = study.plan_day()
    mistakes = study.mistakes(days=14, limit=5)
    due_reviews = status.get("due_reviews") or []
    return {
        "problem_count": status.get("problem_count", 0),
        "status_counts": status.get("status_counts", {}),
        "mastery_counts": status.get("mastery_counts", {}),
        "active_list": status.get("active_list"),
        "active_list_count": status.get("active_list_count", 0),
        "due_review_count": len(due_reviews),
        "due_reviews": due_reviews[:5],
        "recommended_next": status.get("recommended_next"),
        "latest_session": status.get("latest_session"),
        "daily_target": plan.get("daily_target"),
        "review_shortfall": plan.get("review_shortfall"),
        "new_or_open": (plan.get("new_or_open") or [])[:5],
        "recent_mistakes": mistakes,
    }


def build_decision_context(state: Mapping[str, Any], study: StudyService) -> DecisionContext:
    problem = dict(state.get("selected_problem") or {})
    messages = list(state.get("messages") or [])[-12:]
    recent_messages = [
        {
            "role": str(getattr(message, "type", "message")),
            "content": _message_content(message),
        }
        for message in messages
        if _message_content(message)
    ]
    learner_message = next(
        (item["content"] for item in reversed(recent_messages) if item["role"] in {"human", "user"}),
        "",
    )
    slug = problem.get("slug")
    problem_context = study.problem_context(str(slug)) if slug else None
    if problem_context and isinstance(problem_context.get("note"), str):
        note = problem_context["note"]
        if len(note) > MAX_NOTE_CHARS:
            problem_context = {**problem_context, "note": f"{note[:MAX_NOTE_CHARS]}\n[truncated]"}
    return DecisionContext(
        phase=str(state.get("phase", Phase.COACHING.value)),
        problem=problem,
        routing_mode=state.get("routing_mode", "auto"),
        training_mode=state.get("training_mode"),
        hint_level=int(state.get("hint_level", 0)),
        judge_result=state.get("judge_result"),
        learner_message=learner_message,
        recent_messages=recent_messages,
        problem_context=problem_context,
        study_summary=build_study_summary(study),
    )


OutputModel = TypeVar("OutputModel", bound=BaseModel)


def strict_output_schema(model_type: type[OutputModel]) -> dict[str, Any]:
    """Convert Pydantic output schema to the strict object form Codex requires."""

    schema = model_type.model_json_schema()

    def make_strict(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("type") == "object" or "properties" in value:
                properties = value.get("properties", {})
                value["additionalProperties"] = False
                value["required"] = list(properties)
            for child in value.values():
                make_strict(child)
        elif isinstance(value, list):
            for child in value:
                make_strict(child)

    make_strict(schema)
    return schema


def codex_output_schema() -> dict[str, Any]:
    return strict_output_schema(TurnDecision)


def _failed_teach_back(response: str) -> TeachBackDecision:
    return TeachBackDecision(
        assessment=TeachBackAssessment(
            invariant_correct=False,
            complexity_correct=False,
            edge_case_identified=False,
            pattern_boundary_understood=False,
            suggested_quality=0,
            feedback=response,
        ),
        response=response,
    )


def _codex_error_detail(stderr: str) -> str:
    messages = re.findall(r'"message"\s*:\s*("(?:\\.|[^"\\])*")', stderr)
    if messages:
        try:
            return str(json.loads(messages[-1]))[:500]
        except json.JSONDecodeError:
            pass
    useful = [line.strip() for line in stderr.splitlines() if line.strip() and line.strip() not in {"{", "}"}]
    return (useful[-1] if useful else "Codex CLI exited without an error message.")[:500]


class CodexCliDecisionEngine:
    """Run a bounded, ephemeral Codex agent and validate its decision contract."""

    def __init__(
        self,
        study: StudyService,
        *,
        executable: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 120.0,
        runner: CompletedProcessRunner = subprocess.run,
    ):
        self.study = study
        self.executable = executable
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.runner = runner

    def _command(self, executable: str, workdir: Path, schema_path: Path) -> list[str]:
        command = [
            executable,
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--cd",
            str(workdir),
            "--skip-git-repo-check",
            "--ignore-user-config",
            "--ignore-rules",
            "--color",
            "never",
            "--output-schema",
            str(schema_path),
        ]
        if self.model:
            command.extend(["--model", self.model])
        command.append("-")
        return command

    @staticmethod
    def _prompt(context: DecisionContext) -> str:
        return (
            f"{COACH_SYSTEM_PROMPT}\n\n"
            "You are a bounded decision engine inside a LangGraph workflow. "
            "Do not inspect files, run tools, use the shell, access the network, or modify anything. "
            "Use only the authoritative JSON context below. LangGraph owns routing, checkpoints, approvals, "
            "and persistence. Answer progress, count, review, and plan questions from study_summary; never guess. "
            "When the learner explicitly asks to enter or leave pattern-sweep routing, return action=switch_mode "
            "and requested_mode=pattern-sweep or auto. Do not merely claim that a mode changed in response text. "
            "After AC, return action=teach_back only when the learner is actually providing or continuing their "
            "teach-back; answer unrelated questions with action=continue. "
            "Return action=select_next when the learner explicitly asks to start/resume training or choose a problem; "
            "answer progress and status questions with action=continue even when no problem is selected yet. "
            "Return exactly one TurnDecision matching the supplied JSON Schema.\n\n"
            f"Authoritative decision context:\n{context.model_dump_json(indent=2)}"
        )

    @staticmethod
    def _teach_back_prompt(context: DecisionContext) -> str:
        return (
            f"{COACH_SYSTEM_PROMPT}\n\n"
            "You are a bounded teach-back evaluator inside a LangGraph workflow. "
            "Do not inspect files, run tools, use the shell, access the network, or modify anything. "
            "Use only the authoritative JSON context and evaluate the cumulative teach-back after the accepted "
            "solution. Independently assess the invariant, time/space complexity, one valid easy-to-miss edge "
            "case, and a concrete boundary where the pattern does not apply. Return exactly one "
            "TeachBackDecision. The workflow computes completion only from the four booleans; never claim "
            "completion in response prose unless all four are true.\n\n"
            f"Authoritative decision context:\n{context.model_dump_json(indent=2)}"
        )

    def _invoke(
        self,
        state: Mapping[str, Any],
        model_type: type[OutputModel],
        prompt_builder: Callable[[DecisionContext], str],
    ) -> tuple[OutputModel | None, str | None]:
        executable = find_codex_executable(self.executable)
        if not executable:
            return None, "找不到 Codex CLI。请安装 Codex 或设置 LEETCODE_COACH_CODEX_BIN 后重启 Agent Server。"
        context = build_decision_context(state, self.study)
        try:
            with tempfile.TemporaryDirectory(prefix="leetcode-coach-codex-") as raw_workdir:
                workdir = Path(raw_workdir)
                schema_path = workdir / "decision.schema.json"
                schema_path.write_text(json.dumps(strict_output_schema(model_type)), encoding="utf-8")
                completed = self.runner(
                    self._command(executable, workdir, schema_path),
                    input=prompt_builder(context),
                    text=True,
                    capture_output=True,
                    timeout=self.timeout_seconds,
                    cwd=workdir,
                    check=False,
                )
        except subprocess.TimeoutExpired:
            return None, f"Codex decision 超过 {self.timeout_seconds:g} 秒，未改变任何学习数据。请重试。"
        except OSError as exc:
            return None, f"无法启动 Codex CLI：{exc}"
        if completed.returncode != 0:
            detail = _codex_error_detail(completed.stderr or "")
            return None, f"Codex decision 执行失败（exit {completed.returncode}）：{detail[:500]}"
        try:
            return model_type.model_validate_json(completed.stdout.strip()), None
        except Exception:
            return None, f"Codex 返回了无法通过 {model_type.__name__} schema 校验的结果；未改变任何学习数据。"

    def decide(self, state: Mapping[str, Any]) -> TurnDecision:
        result, error = self._invoke(state, TurnDecision, self._prompt)
        if isinstance(result, TurnDecision):
            return result
        return TurnDecision(action="continue", response=error or "Decision failed")

    def assess_teach_back(self, state: Mapping[str, Any]) -> TeachBackDecision:
        result, error = self._invoke(state, TeachBackDecision, self._teach_back_prompt)
        if isinstance(result, TeachBackDecision):
            return result
        return _failed_teach_back(error or "Teach-back evaluation failed")


def build_decision_engine(config: AppConfig, study: StudyService, sweep: PatternSweepService) -> DecisionEngine:
    if config.engine == "codex-cli":
        return CodexCliDecisionEngine(
            study,
            executable=config.codex_bin,
            model=config.codex_model,
            timeout_seconds=config.codex_timeout_seconds,
        )
    return LazyLangChainDecisionEngine(config.model, study, sweep)


__all__ = [
    "CodexCliDecisionEngine",
    "DecisionEngine",
    "LangChainDecisionEngine",
    "LazyLangChainDecisionEngine",
    "build_decision_context",
    "build_decision_engine",
    "build_study_summary",
    "codex_output_schema",
    "find_codex_executable",
    "strict_output_schema",
]
