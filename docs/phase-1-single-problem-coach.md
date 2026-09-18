# Phase 1: reliable single-problem coach

Phase 1 is the first usable product milestone. It deliberately covers one
problem at a time. Multi-problem lessons, a concept-level learner model, and an
Obsidian dashboard belong to later phases.

**Status:** complete as of 2026-09-18. The offline suite passes with 59 tests,
and repository validation plus the local `status` and `plan` smoke tests pass.

## User outcome

The learner can start or resume practice and complete this loop:

```text
select
  -> clarify and restate
  -> propose brute force
  -> receive progressive coaching
  -> implement and submit
  -> debug judge failures
  -> report AC
  -> complete teach-back
  -> approve one completion write
  -> persist the result atomically
```

## Behavioral contract

The coach:

- asks for learner reasoning before revealing the key observation;
- gives progressively stronger hints;
- answers clarification and conceptual questions without corrupting workflow
  state;
- uses the smallest useful counterexample for debugging;
- records WA, TLE, RE, and MLE evidence even when a later submission is AC;
- never infers AC from code review;
- requires explicit AC before teach-back can complete;
- assesses invariant, complexity, an edge case, and pattern boundary;
- never marks mastery `solid` without complete teach-back evidence;
- never claims data was saved before persistence succeeds.

## Reliability contract

- The decision engine sees bounded, read-only context.
- Decision-engine output is schema validated.
- LangGraph owns workflow state and checkpoints.
- Deterministic services own scheduling and persistence rules.
- Initialization and completion require an explicit approval.
- A completion groups solution archive, attempt metadata, pattern coverage, and
  session logging under one rollback boundary.
- Rejection leaves learning data unchanged.
- Offline tests require no model credentials or live MCP server.

## Canonical components

| Component | Responsibility |
| --- | --- |
| `repository.py` | Problem-note reads and protected filesystem transaction |
| `scheduler.py` | Due reviews, daily plan, mistakes, and next selection |
| `attempts.py` | Atomic single-attempt completion workflow |
| `engines.py` | Bounded Codex and LangChain decision adapters |
| `graph.py` | Single-problem conversation state and approval routing |
| `services.py` | Compatibility facade during legacy-script extraction |
| `cli.py` | Stable local entry point |

## Acceptance coverage

Automated tests cover:

- deterministic command recognition;
- bounded decision context and strict structured output;
- initial selection and progressive hint count;
- explicit AC transition;
- incomplete teach-back remaining incomplete;
- one approval for `complete_attempt`;
- rejection without writes;
- rollback after a grouped-write failure;
- chat messages received while approval is pending;
- SQLite checkpoint resume;
- judge-failure history surviving a later AC;
- repository parsing and transaction restoration;
- deterministic scheduling and uninitialized active-list items;
- note, sweep, and session updates after successful completion.

## Phase boundary

Phase 1 ends after one problem is persisted. Asking for the next problem starts
another single-problem loop. A future lesson/session layer may coordinate
multiple activities, but it must reuse this completion boundary rather than
replace it.
