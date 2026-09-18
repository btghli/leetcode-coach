"""Atomic completion workflow for one coached problem attempt."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .schemas import AttemptDraft

if TYPE_CHECKING:
    from .services import PatternSweepService, StudyService


@dataclass(frozen=True)
class CompletionResult:
    attempt_recorded: bool
    archive_completed: bool
    sweep_synchronized: bool
    session_logged: bool


class AttemptService:
    """Execute all durable completion writes inside one rollback boundary."""

    def __init__(self, study: StudyService, sweep: PatternSweepService):
        self.study = study
        self.sweep = sweep

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


__all__ = ["AttemptService", "CompletionResult"]
