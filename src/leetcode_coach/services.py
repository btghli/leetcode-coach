"""Stable application services over the existing repository contracts."""

from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import io
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

from .repository import ProblemRepository, find_root
from .scheduler import StudyScheduler
from .schemas import AttemptDraft, ProblemMetadata


@lru_cache(maxsize=8)
def _load_module(path_string: str, name: str) -> ModuleType:
    path = Path(path_string)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load helper module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class StudyService:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.repository = ProblemRepository(self.root)
        self.scheduler = StudyScheduler(self.repository)
        self.module = _load_module(
            str(self.root / ".codex" / "skills" / "leetcode-coach" / "scripts" / "study.py"),
            "leetcode_coach_legacy_study",
        )

    def _invoke(self, argv: list[str], expect_json: bool = False) -> Any:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = int(self.module.main([*argv, "--root", str(self.root)]) or 0)
        if code:
            raise RuntimeError(stderr.getvalue().strip() or stdout.getvalue().strip() or f"study command failed: {code}")
        output = stdout.getvalue().strip()
        return json.loads(output) if expect_json else output

    def protected_transaction(self):
        return self.repository.protected_transaction()

    def status(self) -> dict[str, Any]:
        return self.scheduler.status()

    def plan_day(self) -> dict[str, Any]:
        return self.scheduler.plan_day()

    def next_problem(self) -> dict[str, Any] | None:
        return self.scheduler.compact(self.scheduler.choose_next())

    def mistakes(self, days: int = 14, limit: int = 5) -> list[dict[str, Any]]:
        return self.scheduler.mistake_summary(days=days, limit=limit)

    def problem_context(self, slug: str) -> dict[str, Any] | None:
        return self.repository.context(slug)

    def initialize_problem(self, metadata: ProblemMetadata) -> dict[str, Any]:
        args = [
            "init-problem", "--id", str(metadata.id), "--slug", metadata.slug,
            "--title", metadata.title, "--difficulty", metadata.difficulty,
            "--tags", ",".join(metadata.tags), "--lists", ",".join(metadata.lists), "--json",
        ]
        return self._invoke(args, expect_json=True)

    def finish_attempt(self, attempt: AttemptDraft) -> dict[str, Any]:
        args = [
            "finish", "--slug", attempt.slug, "--status", attempt.status,
            "--mastery", attempt.mastery, "--mode", attempt.mode,
            "--quality", str(attempt.quality), "--hint-level", str(attempt.hint_level),
            "--teach-back", str(attempt.teach_back).lower(), "--json",
        ]
        if attempt.solve_minutes is not None:
            args += ["--solve-minutes", str(attempt.solve_minutes)]
        if attempt.first_try_ac is not None:
            args += ["--first-try-ac", str(attempt.first_try_ac).lower()]
        if attempt.judge_failures:
            args += ["--judge-failures", ",".join(attempt.judge_failures)]
        if attempt.mistake_tags:
            args += ["--mistake-tags", ",".join(attempt.mistake_tags)]
        return self._invoke(args, expect_json=True)

    def archive_solution(self, slug: str, source: str | None = None) -> str:
        args = ["archive-solution", "--slug", slug, "--mode", "standalone", "--with-tests"]
        args += ["--source", source] if source else ["--from-plugin"]
        return self._invoke(args)

    def plugin_files(self, slug: str) -> list[dict[str, Any]]:
        context = self.problem_context(slug)
        problem_id = context["metadata"].get("id") if context else None
        return self.module.matching_plugin_files(self.root, slug, problem_id)

    def log_session(self, *, problems: list[str], summary: str, next_step: str, mode: str, quality: int) -> dict[str, Any]:
        return self._invoke([
            "log-session", "--problems", ",".join(problems), "--summary", summary,
            "--next", next_step, "--mode", mode, "--quality", str(quality), "--json",
        ], expect_json=True)


class PatternSweepService:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.module = _load_module(
            str(self.root / ".codex" / "skills" / "leetcode-pattern-sweep" / "scripts" / "sweep.py"),
            "leetcode_coach_legacy_sweep",
        )

    def status(self) -> dict[str, Any]:
        state = self.module.progress(self.module.load_state(self.root), self.module.notes(self.root))
        return state

    def recommend_next(self) -> dict[str, Any] | None:
        """Return curriculum work only; reviews belong to the normal study route."""

        state = self.module.progress(self.module.load_state(self.root), self.module.notes(self.root))
        indexed = self.module.notes(self.root)
        category = self.module.next_category(state)
        return self.module.next_in_category(category, indexed) if category else None

    def pattern_card(self, category_slug: str) -> dict[str, Any] | None:
        state = self.module.progress(self.module.load_state(self.root), self.module.notes(self.root))
        category = next((item for item in state["categories"] if item["slug"] == category_slug), None)
        if category is None:
            return None
        path = self.module.pattern_path(self.root, category)
        if not path.is_file():
            return None
        content = path.read_text(encoding="utf-8")
        content = re.sub(
            re.escape(self.module.START) + r".*?" + re.escape(self.module.END),
            "",
            content,
            flags=re.S,
        ).strip()
        return {
            "slug": category["slug"],
            "title": category["title"],
            "subpatterns": [
                {
                    "slug": subpattern["slug"],
                    "title": subpattern["title"],
                    "completed_count": subpattern["completed_count"],
                    "total_count": subpattern["total_count"],
                }
                for subpattern in category["subpatterns"]
            ],
            "content": content[:16_000],
        }

    def catalog_metadata(self, slug: str) -> ProblemMetadata | None:
        for _, _, _, subpatterns in self.module.CATALOG:
            for _, _, problems in subpatterns:
                for problem in problems:
                    if problem["slug"] == slug:
                        return ProblemMetadata(**problem, tags=[], lists=[])
        return None

    def pattern_context(self, slug: str) -> str | None:
        state = self.status()
        for category in state.get("categories", []):
            if category.get("slug") == slug:
                path = self.root / "knowledge" / "patterns" / category["pattern_file"]
                return path.read_text(encoding="utf-8") if path.exists() else None
        return None

    def sync(self) -> dict[str, Any]:
        indexed = self.module.notes(self.root)
        state = self.module.reconcile(self.module.load_state(self.root), indexed)
        self.module.save_state(self.root, state)
        self.module.sync_cards(self.root, state, indexed)
        self.module.sync_progress(self.root, state)
        return state


class MetadataResolver:
    def __init__(
        self,
        study: StudyService,
        sweep: PatternSweepService,
        mcp_config: dict[str, Any] | None = None,
        mcp_client_factory: Any = None,
    ):
        self.study, self.sweep = study, sweep
        self.mcp_config = mcp_config or {}
        self.mcp_client_factory = mcp_client_factory

    async def resolve(self, slug: str) -> ProblemMetadata | None:
        context = await asyncio.to_thread(self.study.problem_context, slug)
        if context:
            raw = context["metadata"]
            if raw.get("id") and raw.get("difficulty") in {"Easy", "Medium", "Hard"}:
                return ProblemMetadata(
                    id=raw["id"], slug=raw["slug"], title=raw["title"], difficulty=raw["difficulty"],
                    tags=raw.get("tags", []), lists=raw.get("lists", []),
                )
        local = await asyncio.to_thread(self.sweep.catalog_metadata, slug)
        if local:
            return local
        if self.mcp_config:
            try:
                return await self._resolve_mcp(slug)
            except Exception:
                return None
        return None

    async def _resolve_mcp(self, slug: str) -> ProblemMetadata | None:
        servers = self.mcp_config.get("servers")
        tool_name = self.mcp_config.get("metadata_tool")
        if not isinstance(servers, dict) or not isinstance(tool_name, str):
            return None
        if self.mcp_client_factory:
            client = self.mcp_client_factory(servers)
        else:
            try:
                from langchain_mcp_adapters.client import MultiServerMCPClient
            except ImportError as exc:
                raise RuntimeError("Install the 'mcp' extra to use MCP metadata resolution") from exc
            client = MultiServerMCPClient(servers)
        tools = await client.get_tools()
        selected = next((tool for tool in tools if tool.name == tool_name), None)
        if selected is None:
            return None
        result = await selected.ainvoke({"slug": slug})
        raw = result if isinstance(result, dict) else json.loads(str(result))
        return ProblemMetadata.model_validate(raw)
