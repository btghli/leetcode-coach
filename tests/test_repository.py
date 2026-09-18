import pytest

from leetcode_coach.repository import ProblemRepository, find_root
from leetcode_coach.schemas import ProblemMetadata
from leetcode_coach.services import StudyService


def test_problem_repository_reads_initialized_note(study_repo):
    study = StudyService(study_repo)
    study.initialize_problem(ProblemMetadata(
        id=1,
        slug="two-sum",
        title="Two Sum",
        difficulty="Easy",
        tags=["array", "hash-table"],
        lists=["example"],
    ))

    repository = ProblemRepository(study_repo)
    context = repository.context("two-sum")

    assert context is not None
    assert context["metadata"]["id"] == 1
    assert context["metadata"]["stats"]["attempts"] == 0
    assert context["note"].startswith("<!-- leetcode-meta")
    assert find_root(context_path := repository.note_paths()[0]) == study_repo
    assert context_path.name == "note.md"


def test_problem_repository_reports_invalid_note(study_repo):
    note = study_repo / "problems" / "0000-0999" / "0001-broken" / "note.md"
    note.parent.mkdir(parents=True)
    note.write_text("# Missing metadata\n", encoding="utf-8")

    items = ProblemRepository(study_repo).all()

    assert len(items) == 1
    assert "missing leetcode-meta block" in items[0]["_error"]


def test_protected_transaction_restores_changed_and_created_files(study_repo):
    original = study_repo / "study" / "goals.md"
    original.write_text("before\n", encoding="utf-8")
    created = study_repo / "knowledge" / "new.md"
    repository = ProblemRepository(study_repo)

    with pytest.raises(RuntimeError, match="rollback"):
        with repository.protected_transaction():
            original.write_text("after\n", encoding="utf-8")
            created.write_text("temporary\n", encoding="utf-8")
            raise RuntimeError("rollback")

    assert original.read_text(encoding="utf-8") == "before\n"
    assert not created.exists()
