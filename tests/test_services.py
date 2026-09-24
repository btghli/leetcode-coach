from pathlib import Path

from leetcode_coach import curriculum
from leetcode_coach.schemas import AttemptDraft, ProblemMetadata
from leetcode_coach.services import MetadataResolver, PatternSweepService, StudyService


def test_study_service_preserves_legacy_contract(study_repo):
    study = StudyService(study_repo)
    before = study.status()
    assert before["problem_count"] == 0
    created = study.initialize_problem(ProblemMetadata(
        id=1, slug="two-sum", title="Two Sum", difficulty="Easy", tags=["array"], lists=["example"],
    ))
    assert created["metadata"]["slug"] == "two-sum"
    plan = study.plan_day()
    assert plan["recommended_next"]["slug"] == "two-sum"

    result = study.finish_attempt(AttemptDraft(
        slug="two-sum", mastery="solid", mode="redo-from-memory", quality=5,
        hint_level=0, teach_back=True,
    ))
    assert result["mastery"] == "solid"


def test_solid_guard_remains_deterministic(study_repo):
    study = StudyService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy"))
    try:
        study.finish_attempt(AttemptDraft(
            slug="two-sum", mastery="solid", mode="guided-solve", quality=3,
            hint_level=1, teach_back=False,
        ))
    except RuntimeError as exc:
        assert "teach_back_done is false" in str(exc)
    else:
        raise AssertionError("solid must be rejected without teach-back")


def test_archive_solution_uses_direct_application_api(study_repo, tmp_path):
    study = StudyService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy"))
    source = tmp_path / "submitted.py"
    source.write_text("class Solution:\n    def answer(self):\n        return 42\n", encoding="utf-8")

    destination = study.archive_solution("two-sum", str(source))

    solution = Path(destination)
    assert solution.name == "solution.py"
    assert solution.parent.name == "0001-two-sum"
    assert "return 42" in solution.read_text(encoding="utf-8")
    assert solution.with_name("test_solution.py").is_file()


async def test_metadata_resolver_local_first(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    resolver = MetadataResolver(study, sweep)
    metadata = await resolver.resolve("two-sum")
    assert metadata and metadata.id == 1
    assert await resolver.resolve("not-in-catalog") is None


async def test_metadata_resolver_mcp_and_safe_fallback(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)

    class Tool:
        name = "get_problem"

        async def ainvoke(self, arguments):
            if arguments["slug"] == "broken":
                raise TimeoutError("offline")
            return {"id": 999, "slug": arguments["slug"], "title": "MCP Problem", "difficulty": "Medium", "tags": []}

    class Client:
        async def get_tools(self):
            return [Tool()]

    resolver = MetadataResolver(
        study,
        sweep,
        {"servers": {"leetcode": {"transport": "stdio"}}, "metadata_tool": "get_problem"},
        mcp_client_factory=lambda _: Client(),
    )
    assert (await resolver.resolve("mcp-problem")).id == 999
    assert await resolver.resolve("broken") is None


def test_pattern_sweep_recommendation_bypasses_due_reviews(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy"))
    item = sweep.recommend_next()
    assert item is not None
    assert item["kind"] == "sweep"
    assert "category" in item and "subpattern" in item


def test_pattern_sweep_finishes_current_category_before_starting_an_untouched_one(study_repo):
    study, sweep = StudyService(study_repo), PatternSweepService(study_repo)
    study.initialize_problem(ProblemMetadata(
        id=19,
        slug="remove-nth-node-from-end-of-list",
        title="Remove Nth Node From End of List",
        difficulty="Medium",
    ))
    study.finish_attempt(AttemptDraft(
        slug="remove-nth-node-from-end-of-list",
        mastery="ok",
        mode="pattern-contrast",
        quality=4,
        hint_level=1,
        teach_back=True,
    ))
    sweep.sync()

    item = sweep.recommend_next()

    assert item is not None
    assert item["category"]["slug"] == "linked-list"
    assert item["subpattern"]["slug"] == "fast-slow"
    assert item["problem"]["slug"] == "linked-list-cycle"


def test_pattern_sweep_prefers_untouched_after_current_category_completes(study_repo):
    sweep = PatternSweepService(study_repo)
    state = curriculum.progress(curriculum.default_state(), {})
    by_slug = {category["slug"]: category for category in state["categories"]}
    by_slug["sliding-window"]["started_at"] = "2026-07-30"
    by_slug["linked-list"]["started_at"] = "2026-08-03"
    by_slug["linked-list"]["completed"] = True
    state["current_focus"] = {"category": "linked-list"}

    category = curriculum.next_category(state)

    assert category["slug"] == "array-hash"


def test_pattern_sweep_legacy_state_advances_after_most_recent_category_completes(study_repo):
    sweep = PatternSweepService(study_repo)
    state = curriculum.progress(curriculum.default_state(), {})
    by_slug = {category["slug"]: category for category in state["categories"]}
    by_slug["sliding-window"]["started_at"] = "2026-07-30"
    by_slug["linked-list"]["started_at"] = "2026-08-03"
    by_slug["linked-list"]["completed"] = True

    category = curriculum.next_category(state)

    assert category["slug"] == "array-hash"


def test_pattern_card_excludes_generated_sweep_map(study_repo):
    sweep = PatternSweepService(study_repo)
    sweep.sync()
    card = sweep.pattern_card("array-hash")
    assert card and card["title"] == "数组与哈希"
    assert card["subpatterns"][0]["title"] == "计数与索引"
    assert "sweep-map:start" not in card["content"]


def test_pattern_sweep_sync_writes_progress_mirror(study_repo):
    sweep = PatternSweepService(study_repo)

    sweep.sync()

    progress = study_repo / "knowledge" / "patterns" / "PROGRESS.md"
    assert progress.is_file()
    content = progress.read_text(encoding="utf-8")
    assert "权威进度源" in content
    assert "[数组与哈希](./array-hash.md)" in content


def test_pattern_sweep_load_merges_expanded_catalog(study_repo):
    sweep = PatternSweepService(study_repo)
    old = curriculum.default_state()
    old["categories"] = old["categories"][:1]
    old["categories"][0]["started_at"] = "2026-01-02"
    curriculum.save_state(study_repo, old)

    merged = curriculum.load_state(study_repo)

    assert merged["categories"][0]["started_at"] == "2026-01-02"
    assert len(merged["categories"]) == len(curriculum.CATALOG)
    assert merged["categories"][-1]["slug"] == "data-structure-design"
