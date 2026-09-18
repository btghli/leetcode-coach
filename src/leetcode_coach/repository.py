"""Canonical filesystem access for durable LeetCode Coach study data.

This module deliberately contains no scheduling or conversational behavior.
It owns repository discovery, problem-note metadata parsing, and the protected
filesystem transaction used by grouped learning-data writes.
"""

from __future__ import annotations

import contextlib
import json
import re
from pathlib import Path
from typing import Any, Iterator


META_RE = re.compile(r"<!--\s*leetcode-meta\s*(\{.*?\})\s*-->", re.DOTALL)
PROTECTED_ROOTS = ("problems", "study", "knowledge")


def find_root(start: Path | None = None) -> Path:
    """Find the nearest directory containing the durable study workspace."""

    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "study" / "profile.json").exists() and (candidate / "problems").exists():
            return candidate
    raise ValueError("LeetCode Coach repository not found")


def _unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if value is not None and value not in result:
            result.append(value)
    return result


def _normalize_stats(value: Any) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "attempts": 0,
        "hint_level_reached": 0,
        "solve_minutes": None,
        "first_try_ac": None,
        "judge_failures": [],
        "recall_score": None,
        "teach_back_done": False,
        "last_mode": None,
    }
    if isinstance(value, dict):
        stats.update(value)
    for field in ("attempts", "hint_level_reached"):
        try:
            stats[field] = int(stats.get(field) or 0)
        except (TypeError, ValueError):
            stats[field] = 0
    failures = stats.get("judge_failures") or []
    if isinstance(failures, str):
        failures = [item.strip() for item in failures.split(",") if item.strip()]
    stats["judge_failures"] = _unique(list(failures))
    return stats


def normalize_problem_metadata(value: dict[str, Any]) -> dict[str, Any]:
    """Apply backward-compatible defaults without changing the note on disk."""

    metadata = dict(value)
    metadata["tags"] = _unique(list(metadata.get("tags") or []))
    metadata["lists"] = _unique(list(metadata.get("lists") or []))
    metadata["mistake_tags"] = _unique(list(metadata.get("mistake_tags") or []))
    metadata.setdefault("status", "Todo")
    metadata.setdefault("mastery", "new")
    metadata.setdefault("last_practiced", None)
    metadata.setdefault("next_review", None)
    metadata["stats"] = _normalize_stats(metadata.get("stats"))
    slug = str(metadata.get("slug") or "problem-slug")
    links = {
        "leetcode": f"https://leetcode.com/problems/{slug}/",
        "leetcode_cn": f"https://leetcode.cn/problems/{slug}/",
    }
    if isinstance(metadata.get("links"), dict):
        links.update(metadata["links"])
    metadata["links"] = links
    return metadata


class ProblemRepository:
    """Read durable problem notes without depending on a host-agent skill."""

    def __init__(self, root: Path):
        self.root = root.resolve()

    def note_paths(self) -> list[Path]:
        problems = self.root / "problems"
        if not problems.exists():
            return []
        return sorted(problems.glob("*/*/note.md"))

    def read_metadata(self, path: Path) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8")
        match = META_RE.search(text)
        if not match:
            raise ValueError(f"missing leetcode-meta block: {path}")
        metadata = normalize_problem_metadata(json.loads(match.group(1)))
        metadata["_path"] = str(path)
        return metadata

    def all(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in self.note_paths():
            try:
                items.append(self.read_metadata(path))
            except Exception as exc:  # noqa: BLE001 - surface invalid notes to validation callers
                items.append({"_path": str(path), "_error": str(exc)})
        return sorted(
            items,
            key=lambda item: (
                item.get("id") is None,
                item.get("id") or 0,
                item.get("slug") or "",
            ),
        )

    def find(self, slug: str) -> tuple[Path, dict[str, Any]] | None:
        for path in self.note_paths():
            metadata = self.read_metadata(path)
            if metadata.get("slug") == slug:
                return path, metadata
        return None

    def context(self, slug: str) -> dict[str, Any] | None:
        found = self.find(slug)
        if not found:
            return None
        path, metadata = found
        return {
            "metadata": {key: value for key, value in metadata.items() if not key.startswith("_")},
            "note": path.read_text(encoding="utf-8"),
        }

    @contextlib.contextmanager
    def protected_transaction(self) -> Iterator[None]:
        """Roll back protected learning files when a grouped write fails."""

        roots = [self.root / name for name in PROTECTED_ROOTS]
        before = {
            path.relative_to(self.root): path.read_bytes()
            for root in roots
            if root.exists()
            for path in root.rglob("*")
            if path.is_file()
        }
        try:
            yield
        except Exception:
            current = {
                path.relative_to(self.root): path
                for root in roots
                if root.exists()
                for path in root.rglob("*")
                if path.is_file()
            }
            for relative, path in current.items():
                if relative not in before:
                    path.unlink()
            for relative, content in before.items():
                path = self.root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists() or path.read_bytes() != content:
                    path.write_bytes(content)
            raise


__all__ = [
    "META_RE",
    "PROTECTED_ROOTS",
    "ProblemRepository",
    "find_root",
    "normalize_problem_metadata",
]
