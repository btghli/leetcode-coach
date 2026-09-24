# LeetCode Coach architecture

This document describes the repository as it exists today, the ownership
boundaries that must remain stable, and the intended direction for simplifying
the implementation.

## System at a glance

The repository contains three systems:

1. **Learning data**: problem notes, solutions, curriculum progress, and study
   sessions.
2. **Deterministic application logic**: scheduling, selection, validation,
   persistence, and solution archiving.
3. **Conversation adapters**: LangGraph orchestration, decision engines, CLI,
   browser UI, and host-agent skills.

The current product milestone is the reliable single-problem coach documented
in `docs/phase-1-single-problem-coach.md`.

The current runtime dependency flow is:

```text
CLI / Agent Server / Browser UI
              |
              v
        TrainingGraph
    conversation + approval
              |
              +----> DecisionEngine
              |       Codex CLI / LangChain
              |       (validated decisions only)
              |
              v
 StudyService / PatternSweepService
              |
              v
 .codex/skills/*/scripts/*.py
              |
              v
 problems/ + study/ + knowledge/
```

The unusual part is the dependency from the installed application under
`src/leetcode_coach/` back into scripts packaged with the Codex skills. This is
the main architectural seam to remove during simplification.

## Authoritative data

These files are durable learning data rather than application caches:

| Data | Source of truth |
| --- | --- |
| Per-problem progress and review metadata | `problems/**/note.md` |
| Accepted solution archive | `problems/**/solution.py` |
| Curriculum coverage | `study/pattern-sweep.json` |
| Learner preferences and active list | `study/profile.json` |
| Learning goals | `study/goals.md` |
| Session history | `study/sessions/*.md` |
| Pattern explanations | `knowledge/patterns/*.md` |
| Named problem lists | `lists/*.md` |

The following rules are architectural contracts:

- A problem note's `leetcode-meta` block owns its progress state.
- `study/pattern-sweep.json` owns curriculum coverage.
- `solid` mastery requires completed teach-back evidence.
- Conversation checkpoints do not replace durable learning data.
- Model output never writes learning data directly.
- One approved `complete_attempt` transaction owns the grouped completion
  write.

## Runtime state and generated content

These paths are not sources of learning truth:

| Path | Purpose |
| --- | --- |
| `.cache/leetcode-coach/checkpoints.sqlite` | Local conversation checkpoints |
| `.langgraph_api/` | LangGraph development-server state |
| `.venv/` | Local Python environment |
| `workspace/leetcode/` | VS Code LeetCode extension workspace |
| `output/` | Generated exports and rendered artifacts |
| `__pycache__/`, `.pytest_cache/` | Python and test caches |

Generated content must never be used to reconstruct or override authoritative
study state.

## Application package

`src/leetcode_coach/` currently contains:

| Module | Responsibility |
| --- | --- |
| `schemas.py` | Validated domain and graph-boundary models |
| `config.py` | Project, provider, and checkpoint configuration |
| `study_store.py` | Canonical note writes, solution archive, sessions, validation, and compatibility CLI |
| `curriculum.py` | Canonical pattern catalog, selection, synchronization, and compatibility CLI |
| `services.py` | Typed facades over canonical application modules |
| `engines.py` | Codex CLI, LangChain, and fake decision engines |
| `graph.py` | Selection, conversation state, approval, and persistence flow |
| `cli.py` | Status, planning, sweep, chat, and thread commands |
| `server.py` | LangGraph Agent Server export |
| `ui.py` | Local server and Agent Chat launcher |

The public entry points are:

```text
leetcode-coach status
leetcode-coach plan
leetcode-coach sweep
leetcode-coach chat
leetcode-coach threads
leetcode-coach-ui
```

## Host-agent skills

The skill directories adapt the project to different coding-agent hosts:

```text
.codex/skills/
.claude/skills/
.agents/skills/
```

Skills contain routing instructions and thin compatibility wrappers around the
canonical application package. They do not own scheduling, persistence, or
curriculum business rules. The remaining host-specific implementation is:

| Script | Current responsibility |
| --- | --- |
| `.codex/skills/leetcode-pattern-coach/scripts/pattern_coach.py` | Lightweight pattern-only routing |

The former study and pattern-sweep scripts now import `study_store.py` and
`curriculum.py`; the application never imports from a host skill directory.

## Training lifecycle

The model owns conversational interpretation. LangGraph owns state transitions,
approval, checkpoints, and the persistence boundary.

```text
select problem
      |
      v
coach <--> debug <--> questions
      |
      v
accepted result
      |
      v
one-call teach-back conversation/assessment
      |
      v
complete_attempt preview
      |
      v
one human approval
      |
      v
archive + note + sweep + session
      |
      v
commit together or roll back together
```

The decision engine returns validated conversational intent. It does not own
repository mutations, selection rules, mastery rules, or checkpoint state.

## Directory audiences

Different users should be able to ignore most of the repository:

### Learner and Obsidian view

```text
problems/
study/
knowledge/
lists/
```

### Application developer view

```text
src/
tests/
pyproject.toml
Makefile
langgraph.json
```

### Agent integration view

```text
.codex/skills/
.claude/skills/
.agents/skills/
AGENTS.md
CLAUDE.md
```

### Local and generated view

```text
.cache/
.langgraph_api/
.venv/
workspace/
output/
```

## Complexity hotspots

The current implementation has three main sources of accidental complexity:

1. Write operations and compatibility CLI commands remain concentrated in the
   large canonical `study_store.py` module.
2. `TrainingGraph` still combines conversational routing with approval flow,
   although grouped completion preparation and execution now belong to
   `AttemptService`.
3. Three host-skill trees repeat similar instructions and adapters.

The number of directories is less important than clarifying who owns each
rule. Moving files without first fixing ownership would only rearrange the
complexity.

## Target dependency direction

The target architecture keeps the same user-facing behavior while making the
application package canonical:

```text
Skills / CLI / UI
        |
        v
src/leetcode_coach
        |
        +-- repository: note and session I/O
        +-- scheduler: reviews and next-problem selection
        +-- curriculum: pattern sweep
        +-- attempts: grouped completion transaction
        +-- graph: conversation orchestration only
        |
        v
problems/ + study/ + knowledge/
```

A small target module layout is sufficient:

```text
src/leetcode_coach/
  schemas.py
  repository.py
  scheduler.py
  curriculum.py
  attempts.py
  engines.py
  graph.py
  cli.py
  server.py
  ui.py
```

The exact filenames are secondary. The important constraint is that skill
packages call the application, and the application never imports business
logic from a host-specific skill directory.

## Safe simplification sequence

Refactoring should preserve commands and repository data at every stage:

1. Establish a green baseline with `make check` and `make test`.
2. Keep note parsing, writes, and compatibility commands in the application
   package while leaving thin skill wrappers in place. **Done.**
3. Keep scheduling and planning in the application package. **Done.**
4. Keep pattern catalog and sweep rules in the application package. **Done.**
5. Keep study and pattern-sweep skill scripts as thin wrappers. **Done.**
6. Expose direct write APIs from `study_store.py`; `StudyService` no longer
   invokes CLI commands or redirects process-global stdout. **Done.**
7. Keep grouped attempt preview and persistence in `AttemptService`; approval
   response handling now has one shared path in `TrainingGraph`. **Done.**
8. Reduce duplicated skill instructions after all hosts call the same CLI.
9. Add an optional, read-only Obsidian export layer derived from authoritative
   data.

Every extraction must keep `make check` and `make test` green. Repository-data
changes additionally require validation before they are accepted.

## Obsidian boundary

The repository root can be opened directly as an Obsidian vault. The useful
knowledge surface is limited to `problems/`, `study/`, and `knowledge/`.

Obsidian may edit learner-authored prose, but it must not become a second owner
of problem metadata or pattern-sweep state. Dynamic dashboards should be
generated from the canonical files instead of duplicating manually maintained
status fields.
