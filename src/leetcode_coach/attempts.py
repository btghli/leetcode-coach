"""Atomic completion workflow for one coached problem attempt."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .schemas import AttemptDraft, PendingAction, TeachBackAssessment

if TYPE_CHECKING:
    from .services import PatternSweepService, StudyService


@dataclass(frozen=True)
class CompletionResult:
    attempt_recorded: bool
    archive_completed: bool
    sweep_synchronized: bool
    session_logged: bool


@dataclass(frozen=True)
class CompletionPreview:
    attempt: AttemptDraft
    pending_action: PendingAction
    operations: tuple[str, ...]


class AttemptService:
    """Execute all durable completion writes inside one rollback boundary."""

    def __init__(self, study: StudyService, sweep: PatternSweepService):
        self.study = study
        self.sweep = sweep

    def prepare(
        self,
        *,
        slug: str,
        training_mode: str,
        assessment: TeachBackAssessment,
        hint_level: int,
        judge_failures: list[str],
        archive_completed: bool,
    ) -> CompletionPreview:
        """Build the one durable completion preview from validated evidence."""

        quality = assessment.suggested_quality
        mastery = "solid" if quality == 5 and assessment.complete else ("ok" if quality >= 3 else "shaky")
        attempt = AttemptDraft(
            slug=slug,
            mastery=mastery,
            mode=training_mode,
            quality=quality,
            hint_level=hint_level,
            first_try_ac=not judge_failures,
            judge_failures=judge_failures,
            teach_back=True,
        )
        should_archive = bool(not archive_completed and self.study.plugin_files(slug))
        operations = ["更新题目训练记录", "同步 pattern sweep coverage", "写入 session log"]
        if should_archive:
            operations.insert(0, "归档 VS Code accepted solution")
        pending = PendingAction(
            action="complete_attempt",
            arguments={
                "attempt": attempt.model_dump(),
                "archive_solution": should_archive,
                "sync_pattern_sweep": True,
                "log_session": True,
            },
            description=f"完成 {slug}：" + "、".join(operations),
        )
        return CompletionPreview(attempt=attempt, pending_action=pending, operations=tuple(operations))

    def complete(
        self,
        attempt: AttemptDraft,
        *,
        archive_solution: bool = False,
        sync_pattern_sweep: bool = True,
        log_session: bool = True,
    ) -> CompletionResult:
        archived = False
        synchronized = False
        logged = False
        with self.study.protected_transaction():
            if archive_solution:
                self.study.archive_solution(attempt.slug)
                archived = True
            self.study.finish_attempt(attempt)
            if sync_pattern_sweep:
                self.sweep.sync()
                synchronized = True
            if log_session:
                self.study.log_session(
                    problems=[attempt.slug],
                    summary="完成 AC 与 teach-back",
                    next_step="继续下一题或按 next_review 复习",
                    mode=attempt.mode,
                    quality=attempt.quality,
                )
                logged = True
        return CompletionResult(
            attempt_recorded=True,
            archive_completed=archived,
            sweep_synchronized=synchronized,
            session_logged=logged,
        )


__all__ = ["AttemptService", "CompletionPreview", "CompletionResult"]
