import pytest

from leetcode_coach.attempts import AttemptService
from leetcode_coach.schemas import AttemptDraft, ProblemMetadata
from leetcode_coach.services import PatternSweepService, StudyService


def _attempt() -> AttemptDraft:
    return AttemptDraft(
        slug="two-sum",
        mastery="ok",
        mode="guided-solve",
        quality=4,
        hint_level=1,
        teach_back=True,
    )


def test_complete_attempt_updates_note_sweep_and_session(study_repo):
    study = StudyService(study_repo)
    sweep = PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(
        id=1,
        slug="two-sum",
        title="Two Sum",
        difficulty="Easy",
    ))

    result = AttemptService(study, sweep).complete(_attempt())

    metadata = study.problem_context("two-sum")["metadata"]
    assert result.attempt_recorded is True
    assert result.sweep_synchronized is True
    assert result.session_logged is True
    assert metadata["status"] == "AC"
    assert metadata["stats"]["teach_back_done"] is True
    sessions = list((study_repo / "study" / "sessions").glob("*.md"))
    assert len(sessions) == 1
    assert "two-sum" in sessions[0].read_text(encoding="utf-8")


def test_complete_attempt_rolls_back_all_writes(study_repo, monkeypatch):
    study = StudyService(study_repo)
    sweep = PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(
        id=1,
        slug="two-sum",
        title="Two Sum",
        difficulty="Easy",
    ))
    original = study.repository.find("two-sum")[0].read_text(encoding="utf-8")

    def fail_log_session(**kwargs):
        raise RuntimeError("session failed")

    monkeypatch.setattr(study, "log_session", fail_log_session)

    with pytest.raises(RuntimeError, match="session failed"):
        AttemptService(study, sweep).complete(_attempt())

    restored = study.repository.find("two-sum")[0].read_text(encoding="utf-8")
    assert restored == original
    assert list((study_repo / "study" / "sessions").glob("*.md")) == []
