"""Deterministic review scheduling and next-problem selection."""

from __future__ import annotations

import datetime as dt
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .repository import ProblemRepository


SLUG_RE = re.compile(r"`([a-z0-9][a-z0-9-]*)`")
STATUSES = ("AC", "Doing", "Review", "Todo")
MASTERIES = ("new", "ok", "shaky", "solid")


class StudyScheduler:
    """Build read-only study views from canonical repository data."""

    def __init__(self, repository: ProblemRepository):
        self.repository = repository
        self.root = repository.root

    def profile(self) -> dict[str, Any]:
        path = self.root / "study" / "profile.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def list_slugs(self, list_name: str) -> list[str]:
        path = self.root / "lists" / f"{list_name}.md"
        return SLUG_RE.findall(path.read_text(encoding="utf-8")) if path.exists() else []

    def latest_session(self) -> Path | None:
        folder = self.root / "study" / "sessions"
        sessions = sorted(path for path in folder.glob("*.md") if path.name != ".gitkeep") if folder.exists() else []
        return sessions[-1] if sessions else None

    def problem_index(self) -> dict[str, dict[str, Any]]:
        return {
            item["slug"]: item
            for item in self.repository.all()
            if item.get("slug") and not item.get("_error")
        }

    def due_problems(self, as_of: dt.date | None = None) -> list[dict[str, Any]]:
        date = as_of or dt.date.today()
        due: list[dict[str, Any]] = []
        for item in self.repository.all():
            if item.get("_error"):
                continue
            try:
                next_review = dt.date.fromisoformat(str(item["next_review"])) if item.get("next_review") else None
            except ValueError:
                continue
            if next_review and next_review <= date and item.get("status") in {"AC", "Review"}:
                due.append(item)
        return sorted(due, key=lambda item: (item.get("next_review") or "", item.get("id") or 0))

    def active_candidates(self, active_list: str) -> list[dict[str, Any]]:
        indexed = self.problem_index()
        slugs = self.list_slugs(active_list)
        if slugs:
            return [indexed[slug] for slug in slugs if slug in indexed]
        return [item for item in indexed.values() if active_list in item.get("lists", [])]

    @staticmethod
    def uninitialized(slug: str, reason: str) -> dict[str, Any]:
        return {
            "id": None,
            "slug": slug,
            "title": slug,
            "difficulty": "?",
            "status": "Uninitialized",
            "mastery": "-",
            "next_review": None,
            "_path": None,
            "_reason": reason,
            "needs_mcp": True,
        }

    def active_open_candidates(self, active_list: str) -> list[dict[str, Any]]:
        indexed = self.problem_index()
        slugs = self.list_slugs(active_list)
        items: list[dict[str, Any]] = []
        if slugs:
            for slug in slugs:
                item = indexed.get(slug)
                if item is None:
                    items.append(self.uninitialized(slug, f"active-list:{active_list}:needs-init"))
                elif item.get("status") in {"Doing", "Todo", "Review"}:
                    items.append({**item, "_reason": f"active-list:{active_list}"})
            return items
        for item in indexed.values():
            if active_list in item.get("lists", []) and item.get("status") in {"Doing", "Todo", "Review"}:
                items.append({**item, "_reason": f"active-list:{active_list}"})
        return sorted(items, key=lambda item: (item.get("id") is None, item.get("id") or 0, item.get("slug") or ""))

    def choose_next(self) -> dict[str, Any] | None:
        active_list = self.profile().get("active_list", "example")
        due = self.due_problems()
        if due:
            return {**due[0], "_reason": "due-review"}
        candidates = self.active_candidates(active_list)
        for status in ("Doing", "Todo", "Review"):
            for item in candidates:
                if item.get("status") == status:
                    return {**item, "_reason": f"active-list:{active_list}"}
        known = {item.get("slug") for item in self.repository.all() if not item.get("_error")}
        for slug in self.list_slugs(active_list):
            if slug not in known:
                return self.uninitialized(slug, f"active-list:{active_list}:needs-init")
        for item in self.repository.all():
            if not item.get("_error") and item.get("status") in {"Doing", "Todo", "Review"}:
                return {**item, "_reason": "any-open-problem"}
        return None

    def in_progress_problem(self) -> dict[str, Any] | None:
        items = [item for item in self.repository.all() if not item.get("_error")]
        for status in ("Doing", "Review"):
            found = next((item for item in items if item.get("status") == status), None)
            if found:
                return self.compact(found)
        return None

    def mistake_summary(self, days: int | None = None, limit: int = 10) -> list[dict[str, Any]]:
        cutoff = dt.date.today() - dt.timedelta(days=days) if days is not None else None
        counts: Counter[str] = Counter()
        examples: dict[str, list[str]] = defaultdict(list)
        for item in self.repository.all():
            if item.get("_error"):
                continue
            if cutoff:
                try:
                    practiced = dt.date.fromisoformat(str(item["last_practiced"])) if item.get("last_practiced") else None
                except ValueError:
                    practiced = None
                if not practiced or practiced < cutoff:
                    continue
            for tag in item.get("mistake_tags", []):
                counts[tag] += 1
                if len(examples[tag]) < 5:
                    examples[tag].append(item.get("slug", "?"))
        return [
            {"tag": tag, "count": count, "problems": examples[tag]}
            for tag, count in counts.most_common(limit)
        ]

    @staticmethod
    def compact(item: dict[str, Any] | None) -> dict[str, Any] | None:
        if not item:
            return None
        return {
            "id": item.get("id"),
            "slug": item.get("slug"),
            "title": item.get("title") or item.get("slug"),
            "difficulty": item.get("difficulty"),
            "status": item.get("status"),
            "mastery": item.get("mastery"),
            "next_review": item.get("next_review"),
            "mistake_tags": item.get("mistake_tags", []),
            "stats": item.get("stats", {}),
            "path": item.get("_path"),
            "needs_mcp": bool(item.get("needs_mcp") or item.get("status") == "Uninitialized" or item.get("id") is None),
            "reason": item.get("_reason"),
        }

    @staticmethod
    def _counts(items: list[dict[str, Any]], field: str, allowed: tuple[str, ...]) -> dict[str, int]:
        counts = {value: 0 for value in sorted(allowed)}
        for item in items:
            value = item.get(field, allowed[0])
            counts[value] = counts.get(value, 0) + 1
        return counts

    def status(self) -> dict[str, Any]:
        profile = self.profile()
        items = self.repository.all()
        problems = [item for item in items if not item.get("_error")]
        errors = [item for item in items if item.get("_error")]
        active_list = profile.get("active_list", "example")
        latest_session = self.latest_session()
        return {
            "root": str(self.root),
            "active_list": active_list,
            "problem_count": len(problems),
            "status_counts": self._counts(problems, "status", STATUSES),
            "mastery_counts": self._counts(problems, "mastery", MASTERIES),
            "active_list_count": len(self.active_candidates(active_list)),
            "due_reviews": [self.compact(item) for item in self.due_problems()],
            "recommended_next": self.compact(self.choose_next()),
            "latest_session": str(latest_session) if latest_session else None,
            "top_mistakes_recent": self.mistake_summary(days=14, limit=5),
            "metadata_errors": errors,
        }

    def status_brief(self) -> str:
        status = self.status()
        lines = [
            f"Root: {self.root}",
            f"Active list: {status['active_list']}",
            f"Problems initialized: {status['problem_count']}",
            "Status: " + ", ".join(f"{key}={value}" for key, value in sorted(status["status_counts"].items())),
            "Mastery: " + ", ".join(f"{key}={value}" for key, value in sorted(status["mastery_counts"].items())),
            f"Active list initialized items: {status['active_list_count']}",
            f"Due reviews: {len(status['due_reviews'])}",
        ]
        if status["top_mistakes_recent"]:
            lines.append("Top recent mistakes: " + ", ".join(
                f"{item['tag']}={item['count']}" for item in status["top_mistakes_recent"][:3]
            ))
        recommended = status["recommended_next"]
        if recommended:
            lines.append(f"Recommended next: {recommended.get('id', '?')} {recommended.get('title')} ({recommended.get('reason')})")
        else:
            lines.append("Recommended next: initialize a problem with MCP metadata")
        session = status["latest_session"]
        lines.append(f"Latest session: {Path(session).name if session else '-'}")
        if status["metadata_errors"]:
            lines.append(f"Metadata errors: {len(status['metadata_errors'])}")
        return "\n".join(lines)

    def plan_day(
        self,
        *,
        active_list: str | None = None,
        review_target: int | None = None,
        new_target: int | None = None,
        mistake_days: int = 14,
    ) -> dict[str, Any]:
        profile = self.profile()
        selected_list = active_list or profile.get("active_list", "example")
        target = profile.get("daily_target", {}) if isinstance(profile.get("daily_target"), dict) else {}
        review_count = review_target if review_target is not None else int(target.get("review", 2) or 0)
        new_count = new_target if new_target is not None else int(target.get("new", 2) or 0)
        due = self.due_problems()
        reviews = due[:review_count] if review_count > 0 else []
        review_slugs = {item.get("slug") for item in reviews}
        open_items = [
            item for item in self.active_open_candidates(selected_list)
            if item.get("slug") not in review_slugs
        ]
        new_or_open = open_items[:new_count] if new_count > 0 else []
        recommended = reviews[0] if reviews else (new_or_open[0] if new_or_open else self.choose_next())
        suggested_mode = "redo-from-memory" if reviews else "guided-solve"
        if recommended and recommended.get("status") == "Uninitialized":
            suggested_mode = "guided-solve"
        return {
            "date": dt.date.today().isoformat(),
            "active_list": selected_list,
            "daily_target": {"review": review_count, "new": new_count},
            "review_shortfall": max(0, review_count - len(reviews)),
            "due_review_count": len(due),
            "reviews": [self.compact(item) for item in reviews],
            "new_or_open": [self.compact(item) for item in new_or_open],
            "mistake_hotspots": self.mistake_summary(days=mistake_days, limit=5),
            "recommended_next": self.compact(recommended),
            "suggested_mode": suggested_mode,
        }


__all__ = ["StudyScheduler"]
