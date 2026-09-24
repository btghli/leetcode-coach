"""Validated boundaries shared by the domain, tools, and graph."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Phase(StrEnum):
    LOADING = "loading"
    SELECTING = "selecting"
    PATTERN_CARD = "pattern_card"
    RESOLVING_METADATA = "resolving_metadata"
    COACHING = "coaching"
    DEBUGGING = "debugging"
    TEACH_BACK = "teach_back"
    AWAITING_APPROVAL = "awaiting_approval"
    PERSISTING = "persisting"
    COMPLETE = "complete"


class ProblemMetadata(BaseModel):
    id: int = Field(gt=0)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str = Field(min_length=1)
    difficulty: Literal["Easy", "Medium", "Hard"]
    tags: list[str] = Field(default_factory=list)
    lists: list[str] = Field(default_factory=list)


class AttemptDraft(BaseModel):
    slug: str
    status: Literal["AC", "Review"] = "AC"
    mastery: Literal["shaky", "ok", "solid"] = "ok"
    mode: Literal["blind-solve", "guided-solve", "redo-from-memory", "debug-drill", "pattern-contrast"]
    quality: int = Field(ge=0, le=5)
    hint_level: int = Field(ge=0, le=4)
    solve_minutes: int | None = Field(default=None, ge=0)
    first_try_ac: bool | None = None
    judge_failures: list[str] = Field(default_factory=list)
    mistake_tags: list[str] = Field(default_factory=list)
    teach_back: bool = False


class TeachBackAssessment(BaseModel):
    invariant_correct: bool
    complexity_correct: bool
    edge_case_identified: bool
    pattern_boundary_understood: bool
    suggested_quality: int = Field(ge=0, le=5)
    feedback: str

    @property
    def complete(self) -> bool:
        return all((self.invariant_correct, self.complexity_correct, self.edge_case_identified, self.pattern_boundary_understood))


class PendingAction(BaseModel):
    action: Literal["initialize_problem", "complete_attempt"]
    arguments: dict[str, Any]
    description: str


RoutingMode = Literal["auto", "pattern-sweep"]


class TurnDecision(BaseModel):
    action: Literal[
        "continue", "hint", "judge_failed", "accepted",
        "select_next", "switch_mode", "quit",
    ]
    response: str
    judge_failure: str | None = None
    requested_mode: RoutingMode | None = None


class TeachBackDecision(BaseModel):
    """One teach-back-phase turn, including intent and optional evidence updates."""

    action: Literal["continue", "teach_back"] = "teach_back"
    assessment: TeachBackAssessment
    response: str


class DecisionContext(BaseModel):
    """Minimal, read-only context passed across a decision-engine boundary."""

    phase: str
    problem: dict[str, Any] = Field(default_factory=dict)
    routing_mode: RoutingMode = "auto"
    training_mode: str | None = None
    hint_level: int = Field(default=0, ge=0, le=4)
    judge_result: str | None = None
    learner_message: str
    recent_messages: list[dict[str, str]] = Field(default_factory=list)
    teach_back_evidence: list[str] = Field(default_factory=list)
    problem_context: dict[str, Any] | None = None
    study_summary: dict[str, Any] = Field(default_factory=dict)
