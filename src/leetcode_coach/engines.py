"""Bounded decision-engine adapters used by the LangGraph workflow."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, TypeVar

from pydantic import BaseModel

from langchain.agents import create_agent
from langchain.messages import HumanMessage

from .config import AppConfig, initialize_model
from .message_content import is_accepted_report, normalize_message_content
from .prompts import COACH_SYSTEM_PROMPT
from .schemas import DecisionContext, Phase, TeachBackAssessment, TeachBackDecision, TurnDecision
from .services import PatternSweepService, StudyService
from .observability import get_observer
from .streaming import event_sink
from .codex_stream import CodexStreamError, run_codex_stream


CODEX_DECISION_INSTRUCTIONS = """You are a Chinese LeetCode coach and a bounded workflow decision engine.
Use only the JSON context; never use tools, files, shell, network, or persistence. Give one concise, actionable next step. Prefer a question that makes the learner reason; acknowledge partial correctness before repairing it. For WA/TLE/RE/MLE use judge_failed; never infer AC or saved progress. Give complete code only when explicitly requested. Use switch_mode only for an explicit pattern-sweep/auto request; use select_next only for an explicit start/resume/choose request. Otherwise use continue or hint. Post-AC turns are handled by a separate phase-specific decision and will not be sent here. Return exactly one object matching the supplied schema."""


class DecisionEngine(Protocol):
    def decide(self, state: Mapping[str, Any]) -> TurnDecision: ...

    def assess_teach_back(self, state: Mapping[str, Any]) -> TeachBackDecision: ...


class LangChainDecisionEngine:
    def __init__(self, model: Any, study: StudyService, sweep: PatternSweepService):
        self.study = study
        _ = sweep
        self.agent = create_agent(
            model=model,
            tools=[],
            system_prompt=COACH_SYSTEM_PROMPT,
            response_format=TurnDecision,
        )
        self.teach_back_agent = create_agent(
            model=model,
            tools=[],
            system_prompt=(
                f"{COACH_SYSTEM_PROMPT}\n\n"
                "Handle exactly one turn after an accepted solution. Return action=teach_back only when the learner "
                "is supplying teach-back evidence; set each assessment boolean only from teach_back_evidence. "
                "For questions or unrelated conversation return action=continue and do not claim new evidence. "
                "The workflow derives completion from the booleans; response prose cannot complete it."
            ),
            response_format=TeachBackDecision,
        )

    def decide(self, state: Mapping[str, Any]) -> TurnDecision:
        context = build_decision_context(state, self.study)
        result = self.agent.invoke({"messages": [HumanMessage(content=(
            "Authoritative decision context:\n" + context.model_dump_json(indent=2)
        ))]})
        structured = result.get("structured_response")
        return structured if isinstance(structured, TurnDecision) else TurnDecision.model_validate(structured)

    def assess_teach_back(self, state: Mapping[str, Any]) -> TeachBackDecision:
        context = build_decision_context(state, self.study)
        result = self.teach_back_agent.invoke({"messages": [HumanMessage(content=(
            "Authoritative teach-back context:\n" + context.model_dump_json(indent=2)
        ))]})
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
MAX_MESSAGE_CHARS = 1_800
RECENT_MESSAGE_LIMIT = 4


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

    def compact_problem(item: Any) -> dict[str, Any]:
        if not isinstance(item, dict):
            return {}
        # Scheduler records also contain local paths, full mistake histories and
        # per-attempt statistics. The coach needs only enough identity/context to
        # answer progress questions; the UI retains the complete local record.
        fields = ('id', 'slug', 'title', 'difficulty', 'status', 'mastery', 'next_review', 'reason')
        return {field: item[field] for field in fields if item.get(field) is not None}

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
        "due_reviews": [compact_problem(item) for item in due_reviews[:3]],
        "recommended_next": compact_problem(status.get("recommended_next")),
        "latest_session": status.get("latest_session"),
        "daily_target": plan.get("daily_target"),
        "review_shortfall": plan.get("review_shortfall"),
        "new_or_open": [compact_problem(item) for item in (plan.get("new_or_open") or [])[:3]],
        "recent_mistakes": mistakes,
    }


def build_decision_context(state: Mapping[str, Any], study: StudyService) -> DecisionContext:
    problem = dict(state.get("selected_problem") or {})
    # Keep coaching context deliberately small. The graph and repository retain
    # full history; the decision model only needs the immediate exchange.
    messages = list(state.get("messages") or [])[-RECENT_MESSAGE_LIMIT:]
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
    all_messages = list(state.get("messages") or [])
    start = state.get("teach_back_start_index")
    if not isinstance(start, int) or start < 0 or start > len(all_messages):
        # Backward-compatible fallback for checkpoints created before the
        # evidence boundary was persisted. The boundary is used only to build
        # model context; it never recovers judge state from old chat text.
        start = 0
        for index, message in enumerate(all_messages):
            if getattr(message, "type", "") in {"human", "user"} and is_accepted_report(_message_content(message)):
                start = index + 1
    teach_back_evidence = [
        _message_content(message)
        for message in all_messages[start:]
        if getattr(message, "type", "") in {"human", "user"} and _message_content(message)
    ]
    slug = problem.get("slug")
    local_context = study.problem_context(str(slug)) if slug else None
    # Notes can contain full solutions and grow without bound. They remain local
    # and available in the UI, but are not injected into every model decision.
    problem_context = ({"metadata": local_context.get("metadata", {})}
                       if isinstance(local_context, dict) else None)
    return DecisionContext(
        phase=str(state.get("phase", Phase.COACHING.value)),
        problem=problem,
        routing_mode=state.get("routing_mode", "auto"),
        training_mode=state.get("training_mode"),
        hint_level=int(state.get("hint_level", 0)),
        judge_result=state.get("judge_result"),
        learner_message=learner_message,
        recent_messages=recent_messages,
        teach_back_evidence=teach_back_evidence,
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
        action="continue",
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


def parse_codex_events(stdout: str) -> tuple[str, dict | None]:
    """Keep only the final agent answer and provider usage; never log reasoning/tool events."""
    answer, usage, event_stream = '', None, False
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or 'type' not in event:
            continue
        event_stream = True
        item = event.get('item')
        item = item if isinstance(item, dict) else {}
        if event['type'] == 'item.completed' and item.get('type') == 'agent_message':
            answer = item.get('text', '')
        if event['type'] == 'turn.completed':
            raw = event.get('usage')
            raw = raw if isinstance(raw, dict) else {}
            if all(type(raw.get(k)) is int and raw[k] >= 0 for k in ('input_tokens', 'output_tokens')):
                usage = {'input_tokens': raw['input_tokens'], 'output_tokens': raw['output_tokens'],
                         'total_tokens': raw['input_tokens'] + raw['output_tokens']}
                cached = raw.get('cached_input_tokens')
                if type(cached) is int and 0 <= cached <= raw['input_tokens']:
                    usage['input_token_details'] = {'cache_read': cached}
                reasoning = raw.get('reasoning_output_tokens')
                if type(reasoning) is int and 0 <= reasoning <= raw['output_tokens']:
                    usage['output_token_details'] = {'reasoning': reasoning}
    # Compatibility with custom runners returning a plain structured decision.
    return (answer if event_stream else stdout.strip()), usage


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
            "--json",
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
            f"{CODEX_DECISION_INSTRUCTIONS}\n\n"
            f"Authoritative decision context:\n{context.model_dump_json(indent=2)}"
        )

    @staticmethod
    def _teach_back_prompt(context: DecisionContext) -> str:
        return (
            "You are a bounded Chinese coach handling one turn after an accepted solution. Use only the JSON "
            "context; never use tools, files, shell, network, or persistence. If the latest learner message supplies "
            "or continues teach-back evidence, return action=teach_back and independently assess invariant, "
            "time/space complexity, one valid easy-to-miss edge case, and a concrete pattern boundary. Assessment "
            "booleans must be supported only by teach_back_evidence, never by AI messages. If the learner asks a "
            "question or says something unrelated, return action=continue, answer naturally, and leave all assessment "
            "booleans false. Return exactly one TeachBackDecision matching the schema. Completion comes only from "
            "the four booleans.\n\n"
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
        prompt = prompt_builder(context)
        observer = get_observer(self.study.root)
        metadata = {'engine': 'codex-cli', 'phase': context.phase,
                    'problem_slug': context.problem.get('slug'), 'decision_type': model_type.__name__,
                    'configured_model': self.model or 'CLI default', 'billing': 'codex-login-not-api-billing'}
        with observer.llm(prompt, metadata) if observer else nullcontext(None) as run:
            result, error, usage = self._execute(executable, prompt, model_type)
            if run is not None:
                outputs = {'decision': result.model_dump() if result else None,
                           'usage_available': usage is not None}
                if result:
                    outputs['choices'] = [{'message': {'role': 'assistant', 'content': result.response}}]
                if usage is not None:
                    outputs['usage_metadata'] = usage
                run.end(outputs=outputs, error=error)
            return result, error

    def _execute(self, executable, prompt, model_type):
        if event_sink.get() is not None and self.runner is subprocess.run:
            usage = None
            try:
                with tempfile.TemporaryDirectory(prefix='leetcode-coach-stream-') as workdir:
                    output, usage = run_codex_stream(executable, prompt, strict_output_schema(model_type),
                                                    Path(workdir), self.model, self.timeout_seconds)
                return model_type.model_validate_json(output), None, usage
            except subprocess.TimeoutExpired:
                return None, 'Codex 流式回复超时；请重试。', usage
            except (CodexStreamError, OSError):
                return None, 'Codex 流式连接失败；请检查 CLI 登录、版本与配置后重试。', usage
            except ValueError:
                return None, f'Codex 返回无法通过 {model_type.__name__} 校验；预览未用于更新学习状态。', usage
        try:
            with tempfile.TemporaryDirectory(prefix="leetcode-coach-codex-") as raw_workdir:
                workdir = Path(raw_workdir)
                schema_path = workdir / "decision.schema.json"
                schema_path.write_text(json.dumps(strict_output_schema(model_type)), encoding="utf-8")
                completed = self.runner(
                    self._command(executable, workdir, schema_path),
                    input=prompt,
                    text=True,
                    capture_output=True,
                    timeout=self.timeout_seconds,
                    cwd=workdir,
                    check=False,
                )
        except subprocess.TimeoutExpired:
            return None, f"Codex decision 超过 {self.timeout_seconds:g} 秒，未改变任何学习数据。请重试。", None
        except OSError as exc:
            return None, f"无法启动 Codex CLI：{exc}", None
        output, usage = parse_codex_events(completed.stdout or '')
        if completed.returncode != 0:
            detail = _codex_error_detail(completed.stderr or "")
            return None, f"Codex decision 执行失败（exit {completed.returncode}）：{detail[:500]}", usage
        try:
            return model_type.model_validate_json(output), None, usage
        except Exception:
            return None, f"Codex 返回了无法通过 {model_type.__name__} schema 校验的结果；未改变任何学习数据。", usage

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
