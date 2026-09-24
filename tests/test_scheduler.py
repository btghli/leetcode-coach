import datetime as dt

from leetcode_coach.repository import ProblemRepository
from leetcode_coach.scheduler import StudyScheduler
from leetcode_coach.schemas import AttemptDraft, ProblemMetadata
from leetcode_coach.services import StudyService


def test_scheduler_selects_due_review_before_open_problem(study_repo):
    study = StudyService(study_repo)
    study.initialize_problem(ProblemMetadata(
        id=1,
        slug="two-sum",
        title="Two Sum",
        difficulty="Easy",
        lists=["example"],
    ))
    study.finish_attempt(AttemptDraft(
        slug="two-sum",
        mastery="ok",
        mode="redo-from-memory",
        quality=3,
        hint_level=0,
        teach_back=True,
    ))
    note = study.repository.find("two-sum")[0]
    study.module.update_note_meta(
        note,
        {
            "next_review": (dt.date.today() - dt.timedelta(days=1)).isoformat(),
            "last_practiced": (dt.date.today() - dt.timedelta(days=2)).isoformat(),
        },
    )

    selected = StudyScheduler(ProblemRepository(study_repo)).choose_next()

    assert selected is not None
    assert selected["slug"] == "two-sum"
    assert selected["_reason"] == "due-review"


def test_scheduler_skips_a_due_problem_practiced_today(study_repo):
    study = StudyService(study_repo)
    study.initialize_problem(ProblemMetadata(
        id=1, slug="two-sum", title="Two Sum", difficulty="Easy", lists=["example"],
    ))
    note = study.repository.find("two-sum")[0]
    today = dt.date.today().isoformat()
    study.module.update_note_meta(note, {"status": "AC", "next_review": "2020-01-01", "last_practiced": today})

    assert StudyScheduler(ProblemRepository(study_repo)).due_problems() == []


def test_scheduler_reports_uninitialized_active_list_problem(study_repo):
    scheduler = StudyScheduler(ProblemRepository(study_repo))

    plan = scheduler.plan_day()

    assert plan["recommended_next"]["slug"] == "two-sum"
    assert plan["recommended_next"]["needs_mcp"] is True
    assert plan["suggested_mode"] == "guided-solve"


def test_status_brief_uses_canonical_scheduler(study_repo):
    brief = StudyScheduler(ProblemRepository(study_repo)).status_brief()

    assert "Problems initialized: 0" in brief
    assert "Recommended next: None two-sum" in brief
