from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def offline_tracing(monkeypatch):
    """Tests never upload learner records, even on a developer's configured machine."""
    from leetcode_coach.observability import get_observer
    monkeypatch.setenv('LANGSMITH_TRACING', 'false')
    monkeypatch.delenv('LANGCHAIN_TRACING_V2', raising=False)
    get_observer.cache_clear()
    yield
    get_observer.cache_clear()


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def study_repo(tmp_path: Path, repo_root: Path) -> Path:
    for name in ("templates",):
        shutil.copytree(repo_root / name, tmp_path / name)
    (tmp_path / "study" / "sessions").mkdir(parents=True)
    (tmp_path / "problems").mkdir()
    (tmp_path / "lists").mkdir()
    (tmp_path / "knowledge" / "patterns").mkdir(parents=True)
    profile = {
        "language": "python3",
        "communication_language": "zh-CN",
        "active_list": "example",
        "daily_target": {"review": 1, "new": 1},
        "review_intervals_days": [1, 7, 30],
        "solid_requires_teach_back": True,
    }
    (tmp_path / "study" / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
    (tmp_path / "lists" / "example.md").write_text("- `two-sum`\n", encoding="utf-8")
    return tmp_path
