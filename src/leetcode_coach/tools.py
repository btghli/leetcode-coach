"""Narrow, typed, read-only tools exposed to the coaching agent."""

from __future__ import annotations

from langchain.tools import tool

from .services import PatternSweepService, StudyService


def build_read_tools(study: StudyService, sweep: PatternSweepService):
    @tool
    def get_study_status() -> dict:
        """Read the learner's current aggregate progress and due reviews."""
        return study.status()

    @tool
    def plan_study_day() -> dict:
        """Build today's deterministic review and new-problem plan."""
        return study.plan_day()

    @tool
    def get_next_problem() -> dict | None:
        """Read the deterministic next problem recommendation."""
        return study.next_problem()

    @tool
    def get_problem_context(slug: str) -> dict | None:
        """Read a problem's metadata and learner-authored note by slug."""
        return study.problem_context(slug)

    @tool
    def get_pattern_context(pattern_slug: str) -> str | None:
        """Read the local pattern card for a pattern slug."""
        return sweep.pattern_context(pattern_slug)

    @tool
    def summarize_recent_mistakes(days: int = 14, limit: int = 5) -> list[dict]:
        """Summarize recent mistake tags without changing study data."""
        return study.mistakes(days=days, limit=limit)

    return [get_study_status, plan_study_day, get_next_problem, get_problem_context, get_pattern_context, summarize_recent_mistakes]
