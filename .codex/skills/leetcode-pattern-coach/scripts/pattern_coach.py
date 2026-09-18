#!/usr/bin/env python3
"""Deterministic, curriculum-only selector for direct pattern coaching."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType


def repository_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    candidates = (Path.cwd().resolve(), *Path.cwd().resolve().parents)
    for candidate in candidates:
        if (candidate / "study" / "pattern-sweep.json").is_file() and (candidate / "knowledge" / "patterns").is_dir():
            return candidate
    packaged = Path(__file__).resolve().parents[4]
    if (packaged / "study" / "pattern-sweep.json").is_file():
        return packaged
    raise SystemExit("LeetCode Coach repository not found; pass --root.")


def load_sweep(root: Path) -> ModuleType:
    path = root / ".codex" / "skills" / "leetcode-pattern-sweep" / "scripts" / "sweep.py"
    if not path.is_file():
        raise SystemExit(f"Pattern sweep helper not found: {path}")
    spec = importlib.util.spec_from_file_location("leetcode_pattern_coach_sweep", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load pattern sweep helper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compact_category(category: dict) -> dict:
    return {
        "slug": category["slug"],
        "title": category["title"],
        "pattern_file": category["pattern_file"],
        "completed_count": category["completed_count"],
        "total_count": category["total_count"],
        "completed": category["completed"],
        "started_at": category.get("started_at"),
        "completed_at": category.get("completed_at"),
        "subpatterns": [
            {
                "slug": subpattern["slug"],
                "title": subpattern["title"],
                "completed_count": subpattern["completed_count"],
                "total_count": subpattern["total_count"],
                "completed": subpattern["completed"],
            }
            for subpattern in category["subpatterns"]
        ],
    }


def command_status(args: argparse.Namespace) -> int:
    root = repository_root(args.root)
    sweep = load_sweep(root)
    indexed = sweep.notes(root)
    state = sweep.progress(sweep.load_state(root), indexed)
    payload = {
        "root": str(root),
        "current_focus": state.get("current_focus"),
        "completed_count": sum(category["completed_count"] for category in state["categories"]),
        "total_count": sum(category["total_count"] for category in state["categories"]),
        "categories": [compact_category(category) for category in state["categories"]],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def selected_category(state: dict, sweep: ModuleType, requested: str | None) -> dict:
    if requested:
        category = next((item for item in state["categories"] if item["slug"] == requested), None)
        if category is None:
            choices = ", ".join(item["slug"] for item in state["categories"])
            raise SystemExit(f"Unknown category {requested!r}. Choose one of: {choices}")
        return category
    category = sweep.next_category(state)
    if category is None:
        raise SystemExit("Pattern curriculum is complete.")
    return category


def command_next(args: argparse.Namespace) -> int:
    root = repository_root(args.root)
    sweep = load_sweep(root)
    indexed = sweep.notes(root)
    state = sweep.progress(sweep.load_state(root), indexed)
    category = selected_category(state, sweep, args.category)
    item = sweep.next_in_category(category, indexed)
    if item is None:
        payload = {"kind": "category-complete", "category": compact_category(category)}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    focus = state.get("current_focus") or {}
    show_card = focus.get("category") != category["slug"]
    problem = item["problem"]
    payload = {
        "kind": "pattern-problem",
        "category": {"slug": category["slug"], "title": category["title"]},
        "subpattern": {"slug": item["subpattern"]["slug"], "title": item["subpattern"]["title"]},
        "problem": problem,
        "problem_url": f"https://leetcode.com/problems/{problem['slug']}/",
        "pattern_file": str(sweep.pattern_path(root, category)),
        "show_card": show_card,
        "initialized": problem["slug"] in indexed,
    }
    if args.set_focus:
        started_at = sweep.date()
        if not category.get("started_at"):
            category["started_at"] = started_at
        if not item["subpattern"].get("started_at"):
            item["subpattern"]["started_at"] = started_at
        state["current_focus"] = {
            "category": category["slug"],
            "subpattern": item["subpattern"]["slug"],
            "problem_slug": problem["slug"],
            "set_at": started_at,
        }
        sweep.save_state(root, state)
        payload["focus_saved"] = True
    else:
        payload["focus_saved"] = False
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", help="LeetCode Coach repository root")
    subcommands = result.add_subparsers(required=True)

    status = subcommands.add_parser("status", help="Show pattern-only curriculum progress as JSON")
    status.set_defaults(func=command_status)

    next_problem = subcommands.add_parser("next", help="Select the next curriculum problem without due reviews")
    next_problem.add_argument("--category", help="Honor an explicit category slug")
    next_problem.add_argument("--set-focus", action="store_true", help="Persist the selected curriculum focus")
    next_problem.set_defaults(func=command_next)
    return result


if __name__ == "__main__":
    arguments = parser().parse_args()
    raise SystemExit(arguments.func(arguments))
