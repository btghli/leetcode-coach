"""Stable application services over the existing repository contracts."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

from . import curriculum, study_store
from .repository import ProblemRepository, find_root
from .scheduler import StudyScheduler
from .schemas import AttemptDraft, ProblemMetadata


class StudyService:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.repository = ProblemRepository(self.root)
        self.scheduler = StudyScheduler(self.repository)

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
        try:
            return study_store.initialize_problem(
                self.root,
                problem_id=metadata.id,
                slug=metadata.slug,
                title=metadata.title,
                difficulty=metadata.difficulty,
                tags=metadata.tags,
                lists=metadata.lists,
            )
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc

    def finish_attempt(self, attempt: AttemptDraft) -> dict[str, Any]:
        try:
            return study_store.finish_attempt(
                self.root,
                slug=attempt.slug,
                status=attempt.status,
                mastery=attempt.mastery,
                mode=attempt.mode,
                quality=attempt.quality,
                hint_level=attempt.hint_level,
                solve_minutes=attempt.solve_minutes,
                first_try_ac=attempt.first_try_ac,
                judge_failures=attempt.judge_failures or None,
                teach_back=attempt.teach_back,
                allow_unverified_solid=False,
                clear_mistake_tags=False,
                mistake_tags=attempt.mistake_tags,
                next_review=None,
                review_in_days=None,
            )
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc

    def archive_solution(self, slug: str, source: str | None = None) -> str:
        try:
            result = study_store.archive_solution(
                self.root,
                slug=slug,
                source=source,
                from_plugin=source is None,
                mode="standalone",
                with_tests=True,
            )
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc
        return str(result["dest"])

    def plugin_files(self, slug: str) -> list[dict[str, Any]]:
        context = self.problem_context(slug)
        problem_id = context["metadata"].get("id") if context else None
        return study_store.matching_plugin_files(self.root, slug, problem_id)

    def log_session(self, *, problems: list[str], summary: str, next_step: str, mode: str, quality: int) -> dict[str, Any]:
        return study_store.log_session(
            self.root,
            problems=",".join(problems),
            summary=summary,
            next_step=next_step,
            mode=mode,
            quality=quality,
        )


class PatternSweepService:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def status(self) -> dict[str, Any]:
        state = curriculum.progress(curriculum.load_state(self.root), curriculum.notes(self.root))
        return state

    def recommend_next(self) -> dict[str, Any] | None:
        """Return curriculum work only; reviews belong to the normal study route."""

        state = curriculum.progress(curriculum.load_state(self.root), curriculum.notes(self.root))
        indexed = curriculum.notes(self.root)
        category = curriculum.next_category(state)
        return curriculum.next_in_category(category, indexed) if category else None

    def pattern_card(self, category_slug: str) -> dict[str, Any] | None:
        state = curriculum.progress(curriculum.load_state(self.root), curriculum.notes(self.root))
        category = next((item for item in state["categories"] if item["slug"] == category_slug), None)
        if category is None:
            return None
        path = curriculum.pattern_path(self.root, category)
        if not path.is_file():
            return None
        content = path.read_text(encoding="utf-8")
        content = re.sub(
            re.escape(curriculum.START) + r".*?" + re.escape(curriculum.END),
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
        for _, _, _, subpatterns in curriculum.CATALOG:
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
        indexed = curriculum.notes(self.root)
        state = curriculum.reconcile(curriculum.load_state(self.root), indexed)
        curriculum.save_state(self.root, state)
        curriculum.sync_cards(self.root, state, indexed)
        curriculum.sync_progress(self.root, state)
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
