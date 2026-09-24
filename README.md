# LeetCode Coach

[![Checks](https://github.com/guanyipengai/leetcode-coach/actions/workflows/leetcode-coach-check.yml/badge.svg)](https://github.com/guanyipengai/leetcode-coach/actions/workflows/leetcode-coach-check.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)
![LangChain](https://img.shields.io/badge/LangChain-Agent-1C3C3C)
![LangGraph](https://img.shields.io/badge/LangGraph-Workflow-111827)
![VS Code](https://img.shields.io/badge/VS%20Code-LeetCode%20extension-007ACC)
![Status](https://img.shields.io/badge/status-alpha-yellow)

> A local LangChain/LangGraph coaching agent and study workspace that turns LeetCode practice into a review-driven loop: solve in VS Code, get progressive hints, archive accepted solutions, and schedule evidence-based review.

<p align="center">
  <img src="assets/architecture2.png" alt="LeetCode Coach architecture and learning loop" width="920">
</p>


## Why this exists

AI can make LeetCode practice faster, but it can also make it easier to skip the hard part. This project is designed around a stricter loop:

1. Review due problems before starting new ones.
2. Ask for progressive hints instead of full solutions.
3. Submit through the normal LeetCode workflow.
4. Archive only your accepted code and your own explanations.
5. Finish with teach-back before marking a problem as mastered.
6. Schedule the next review from evidence: time, hints, judge failures, recall quality, and mistake tags.

The goal is not to solve more problems with AI. The goal is to remember more of the problems you solve.

## What it does

- **Daily planning**: picks due reviews, active problems, and new problems from your active list.
- **Progressive coaching**: gives hints, counterexamples, edge-case checks, and complexity review without defaulting to answer dumps.
- **VS Code judge flow**: you solve and submit through the VS Code LeetCode extension under `workspace/leetcode/`.
- **Accepted-code archive**: after AC, accepted code is copied into `problems/.../solution.py`.
- **Evidence-based metadata**: tracks attempts, hint level, solve time, first-try AC, judge failures, recall score, teach-back status, and training mode.
- **Adaptive spaced review**: schedules review based on mastery, quality, hints, failures, and repeated mistake patterns.
- **Mistake taxonomy**: turns wrong answers into reusable weakness signals.
- **Pattern notes**: turns repeated ideas into durable templates and decision boundaries.
- **Local validation**: checks metadata and repository contracts with `make check`.

## What it is not

- It is not an official LeetCode project.
- It is not a LeetCode problem mirror.
- It is not an auto-submitter.
- It is not a tool for copying full problem statements or private LeetCode content into Git.
- It is not designed to replace your own reasoning during practice.

## Quick start

### 1. Clone and prepare the workspace

```bash
git clone https://github.com/guanyipengai/leetcode-coach.git
cd leetcode-coach
cp -n study/profile.example.json study/profile.json 2>/dev/null || true
make check
```

Install the application and browser UI server:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,ui,openai,anthropic,mcp]'
```

The default decision engine is the local Codex CLI. Install Codex, sign in with ChatGPT, and verify the safe login status before starting the coach:

```bash
codex login
codex login status
```

The coach invokes Codex ephemerally in a temporary empty directory with a read-only sandbox and a `TurnDecision` JSON Schema. Codex receives only the bounded context prepared by LangGraph, including a compact read-only study summary for progress and planning questions; it does not own checkpoints or business-data writes.

### 2. Install the judge workflow

Install the VS Code LeetCode extension, sign in, and open this repository in VS Code. The repository-level settings keep plugin-generated files under `workspace/leetcode/`, which is ignored by Git.

Optional: configure LeetCode MCP for Codex if you want the coach to fetch problem metadata automatically.

### 3. Start the browser chat UI

Run `make ui`, or double-click `start-leetcode-coach.command` on macOS. This opens the local learning workbench:

```text
http://127.0.0.1:2025
```

The workbench includes learning statistics, curriculum coverage, due reviews,
session notes, single-problem chat, and a searchable library of all 18 pattern
categories. Python skeletons are copied from existing pattern cards; subpatterns
without dedicated templates are labeled as shared category material. Viewing
templates does not change mastery or mark practice complete.

Keep the launcher window open while practicing. The browser remembers the current
thread and restores its LangGraph checkpoint on refresh. Judge shortcuts prepare
a message for you to send. After teach-back, review the proposed changes and
choose **保存练习** or **暂不保存**. Statistics refresh after successful persistence.

For a headless launch or a different port:

```bash
python3 -m leetcode_coach.web --no-browser --port 2025
```

The original Agent Server remains available via `make agent-server`. You can
still connect [Agent Chat UI](https://agentchat.vercel.app) to
`http://localhost:2024`, graph ID `leetcode_coach`. The workbench uses the same
graph directly and the CLI's SQLite checkpoint store; it needs no Agent Server
or hosted frontend.

No API key is required for the default `codex-cli` engine when Codex is already signed in with ChatGPT. To use a standard LangChain provider instead, configure it explicitly before starting the launcher:

```bash
export LEETCODE_COACH_ENGINE=langchain
export LEETCODE_COACH_MODEL=<provider:model-id>
export OPENAI_API_KEY=...      # for an OpenAI model
# or ANTHROPIC_API_KEY=...     # for an Anthropic model
```

For the Codex backend, optional settings are `LEETCODE_COACH_CODEX_MODEL`, `LEETCODE_COACH_CODEX_BIN`, and `LEETCODE_COACH_CODEX_TIMEOUT`. The launcher can open without provider API values; the first decision turn reports missing Codex installation/login or provider configuration without changing learning data. Credentials are never printed or persisted by the project.

### 4. Optional CLI and deterministic commands

Inspect the deterministic plan:

```bash
.venv/bin/leetcode-coach status --brief
.venv/bin/leetcode-coach plan
```

Start the LangGraph loop with the default Codex Subscription backend:

```bash
.venv/bin/leetcode-coach chat \
  --engine codex-cli \
  --thread-id daily-2026-07-30
```

An explicit provider model preserves the original LangChain CLI behavior:

```bash
.venv/bin/leetcode-coach chat \
  --engine langchain \
  --model <provider:model-id> \
  --thread-id daily-2026-07-30
```

Use the same thread ID to resume after exiting. Conversation checkpoints live in the ignored `.cache/leetcode-coach/checkpoints.sqlite`; learning facts remain in problem notes and study files.

From Codex or Claude Code, you can also start with:

```text
用 leetcode-coach，今天开始 LeetCode 训练。
```

or:

```text
Use leetcode-coach. Start today's LeetCode practice.
```

The host agent should route you into the same project-neutral CLI rather than maintaining a separate provider-specific implementation.

## Decision engines and LangGraph architecture

The conversational agent owns natural-language semantics; LangGraph is a thin reliability boundary for selection state, checkpoints, validation, one human approval, and persistence. The model implementation remains swappable:

```text
Agent Chat UI / CLI
        ↓
Conversational DecisionEngine
        ├── CodexCliDecisionEngine → codex exec → ChatGPT Subscription
        ├── LangChainDecisionEngine → init_chat_model/create_agent → provider API or local model
        └── FakeDecisionEngine → offline tests
        ↓
validated coaching action or phase-specific teach-back assessment
        ↓
Thin LangGraph boundary
        ↓
validate → preview all changes → one approval → grouped persist
```

The conversational path is intentionally loose, while the completion boundary is strict:

```text
select → coach ⇄ debug ⇄ questions
                    ↓ accepted
          conversational teach-back
                    ↓ complete assessment
       one complete_attempt approval
                    ↓
 archive + note + sweep + session (rollback together on failure)
```

Scheduling, mastery guards, note updates, and pattern completion remain deterministic Python services. The Codex adapter runs in an empty temporary working directory with `--ephemeral`, `--sandbox read-only`, ignored user config/rules, and structured output validation. LangChain is an optional provider adapter, not a requirement for the Codex engine. Critical writes remain outside every decision engine.

`TurnDecision` handles coaching and debugging intent. After AC, the graph calls `TeachBackDecision` directly, so one learner message produces at most one model reply. That phase-specific decision distinguishes evidence from ordinary conversation and evaluates the four required fields only from learner messages recorded after the current problem's AC event. Assistant prose cannot become evidence or complete an attempt.

Completion produces one `complete_attempt` preview covering solution archive (when present), note/mastery update, pattern sweep sync, and session log. One approve/edit/reject decision covers that grouped operation; any internal failure restores all protected learning files. If UI approval controls are hidden, send the exact command `批准` / `approve` or `拒绝` / `reject`. `下一题` never implies approval.

Normal routing is owned by `StudyScheduler`: resume current Doing/Review work, then choose a due review, then active-list work. Pattern representatives are selected only in explicit pattern-sweep mode. Optional problem metadata lookup uses `langchain-mcp-adapters`; copy `leetcode-coach.toml.example` to `leetcode-coach.toml` to configure it. Without MCP, the application uses existing notes and the local sweep catalog, then requests structured human confirmation instead of guessing metadata.

In chat, you can say `切换到题型扫荡模式` (or switch back with `切换到自动选题模式`). The decision engine returns a structured `switch_mode` intent; LangGraph validates it and stores `routing_mode` in the thread. Pattern sweep is a separate new-curriculum lane: it bypasses due reviews, current Doing/Review work, and the active list; finishes the current started pattern category before switching; then chooses the first wholly untouched pattern, returning to other partially covered categories only after every category has started. It presents each newly selected pattern's card and pauses, then advances through its uncovered subpatterns and representative problems one at a time. `routing_mode` controls curriculum selection, while `training_mode` controls how the selected problem is practiced.

All automated tests use fake decision engines and temporary study repositories, so CI requires neither API keys nor live MCP servers. LangSmith tracing is optional and is not required for local use.


## Repository layout

```text
src/leetcode_coach/                # Domain services, decision adapters, LangGraph, and CLI
.codex/ and .claude/               # Thin host-agent adapters
.github/workflows/                 # CI validation
.vscode/settings.json              # VS Code LeetCode workspace settings
docs/                              # Demo and troubleshooting notes
knowledge/mistake-taxonomy.md      # Standard mistake tags
knowledge/patterns/                # Reusable pattern notes
lists/                             # Study lists by LeetCode slug
problems/                          # One directory per initialized problem
study/goals.md                     # Learning goals and current focus
study/profile.json                 # Personal preferences and active list
study/sessions/                    # Daily session logs
templates/                         # Note, session, pattern, and code templates
workspace/leetcode/                # Ignored VS Code LeetCode submit workspace
```

Problem folders are grouped by frontend ID:

```text
problems/
  0000-0999/
    0001-two-sum/
      note.md
      solution.py
      test_solution.py
```

## Data model

Each `note.md` starts with a JSON metadata block. That block is the source of truth for progress; lists and sessions are derived views or logs.

```json
{
  "id": 1,
  "slug": "two-sum",
  "title": "Two Sum",
  "difficulty": "Easy",
  "tags": ["array", "hash-table"],
  "lists": ["hot100"],
  "status": "Todo",
  "mastery": "new",
  "last_practiced": null,
  "next_review": null,
  "mistake_tags": [],
  "stats": {
    "attempts": 0,
    "hint_level_reached": 0,
    "solve_minutes": null,
    "first_try_ac": null,
    "judge_failures": [],
    "recall_score": null,
    "teach_back_done": false,
    "last_mode": null
  }
}
```

A problem should not be marked `solid` until teach-back is complete. In practice, that means you can explain:

- the invariant or state definition;
- why the chosen pattern works;
- time and space complexity;
- the easiest edge case to miss;
- when this pattern does not apply.

## VS Code LeetCode integration

This repo expects project-level settings similar to:

```json
{
  "leetcode.workspaceFolder": "${workspaceFolder}/workspace/leetcode",
  "leetcode.filePath": "${id}.${kebab-case-name}.${ext}",
  "leetcode.defaultLanguage": "python3",
  "leetcode.endpoint": "leetcode-cn"
}
```

Plugin-generated files are temporary judge files. They should stay ignored by Git. The durable archive lives under `problems/.../` after AC.

## Upgrading older notes

Older problem notes may not include `stats` or `Teach Back`. Preview migration before writing changes:

```bash
make migrate-preview
```

Apply migration:

```bash
make migrate
make check
```

Use strict validation when you want to enforce teach-back evidence for `solid` problems:

```bash
make strict-check
```

## LangSmith observability

The local UI, CLI chat, and graph server can send teaching traces to LangSmith.
Create a LangSmith key and add these settings to the Git-ignored `.env.local`:

```dotenv
LANGSMITH_API_KEY=your-key
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=leetcode-coach
# Set LANGSMITH_ENDPOINT for a non-default region.
# Set LANGSMITH_WORKSPACE_ID if your key needs an explicit workspace.
```

Only tracing settings are read from this file; Codex CLI keeps its existing login.
Process environment values override the file. A configured key enables tracing
unless `LANGSMITH_TRACING=false`; restart the application after changing settings.
The default endpoint is GCP US. This feature sends data to a third-party service.

In LangSmith, open **Tracing Projects → leetcode-coach**:

- Expand a turn to see graph nodes such as `process_turn` and `assess_teach_back`.
- Expand `codex.decision` for the supplied prompt, validated decision, latency and
  CLI-reported input/output/cache token usage. Missing usage is unknown, not zero.
- Group/filter by `thread_id` to inspect a conversation; model-call metadata also
  includes the teaching phase, problem slug and decision type.
- Review long or repetitive turns and add useful examples to evaluation datasets.

Detailed traces contain teaching messages, supplied code and the bounded current
problem context already sent to the model. They do not scan/upload the repository
or Codex auth files. Known environment secrets, common key formats and local home/
temporary paths are redacted before upload, including errors and metadata; raw
Codex reasoning/tool events and serialized runtime objects are excluded. This is
not comprehensive PII detection: do not paste confidential information into chat.

`LANGSMITH_TRACING_SAMPLING_RATE` optionally controls trace sampling (default 1).
Sampled totals are not whole-account usage. Codex subscription usage is not an API
invoice; no model identity or monetary cost is fabricated. Tracing failures do not
intentionally block coaching, and offline tests disable tracing automatically.

The local workbench streams Codex replies over a POST NDJSON connection. It uses
the same Codex CLI login via `codex app-server` and an ephemeral single-turn thread
to receive `item/agentMessage/delta` notifications. LangGraph still exclusively
owns learning conversation state, checkpoints and approval/persistence decisions.
This requires a CLI version supporting app-server, ephemeral threads and output
schemas (verified with 0.153.4). Terminal chat retains its existing exec transport.

While generating, only the structured decision's `response` text is displayed as
an unvalidated preview. The final schema-validated graph state replaces it; partial
JSON never changes mastery or saves a learning record. The model may take time
before its first text delta. On disconnect, the backend finishes/checkpoints the
in-flight turn; refresh before resending, especially around save approvals. No
automatic request retries or simulated typewriter playback are used. LangChain
provider mode currently delivers graph-stage events and a final response, not
token previews. The decision engine controls conversational progression without
a mechanical turn-count cutoff. Each Codex
decision carries only the last four messages (maximum 1,800 characters each) and
problem metadata; full local notes stay local and are never injected into a model
decision.

## Project status

This project is usable as a personal LeetCode training workspace, but it is still early. The most stable parts are the repository contract, problem note format, and deterministic helper commands. Before using it as a public template, consider adding `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and `SECURITY.md`.

## Contributing

Issues and pull requests are welcome, especially for:

- clearer workflows and documentation;
- additional validation checks;
- mistake taxonomy improvements;
- pattern-note examples;
- tests for `study.py`.

Please keep the core principle intact: the coach should improve learning, not bypass it.

## License

MIT License. See [LICENSE](LICENSE).
