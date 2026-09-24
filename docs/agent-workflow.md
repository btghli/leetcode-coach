# Shared LeetCode Coach workflow

Use the canonical CLI instead of inspecting every note manually:

```bash
leetcode-coach status --brief
leetcode-coach plan
```

For an interactive, checkpointed session, run:

```bash
leetcode-coach chat --engine codex-cli --thread-id <stable-id>
```

The Codex decision engine uses the local ChatGPT-authenticated CLI by default. For the LangChain provider path, use `--engine langchain --model <provider:model-id>`.

Coach progressively: clarify, ask for brute force, reveal an observation, establish the invariant, then discuss pseudocode and implementation. Show complete code only after explicit request or sustained difficulty.

After AC, require teach-back covering the invariant, complexity, an easy-to-miss edge case, and when the pattern does not apply. Route each turn directly through the phase-specific teach-back decision so one learner message produces at most one model reply. Assess only human evidence after the current problem's AC boundary; keep unrelated questions conversational and do not update the assessment. Never claim a write succeeded until the graph confirms persistence.

If Agent Chat does not expose the interrupt controls clearly, the learner may send the exact chat command `批准` / `approve` or `拒绝` / `reject`. Ordinary messages such as `下一题` never imply approval: the graph must explain the pending action and present the interrupt again instead of remaining silent.

Normal automatic routing is owned by the scheduler: resume current Doing/Review work, then choose a due review, then active-list work. Pattern-sweep routing is a separate new-curriculum lane: do not select due reviews, current work, or active-list fallback. Finish the current started pattern category before switching categories. When the current category is complete, choose an untouched pattern first; only return to another partially covered category after every category has been started. Show a newly selected pattern's card, pause for the learner, and then advance its uncovered subpatterns and representative problems one at a time. Keep `problems/**/note.md` authoritative for progress and `study/pattern-sweep.json` authoritative for curriculum coverage.

The learner may switch routing in chat by asking for `pattern-sweep` or `auto`. Return a structured `switch_mode` decision with `requested_mode`; do not claim a switch only in prose. LangGraph owns the persisted `routing_mode`, re-selection, and validation. This routing mode is separate from per-problem `training_mode` such as `pattern-contrast` or `redo-from-memory`.

Normalize UI/provider content blocks into plain learner text before interpreting commands. `TurnDecision` represents pre-AC conversational intent; `TeachBackDecision` owns post-AC intent and assessment in one call. Derive completion deterministically from invariant, complexity, edge-case, and pattern-boundary evidence; response prose is never evidence or a write. Once complete, build one `complete_attempt` preview containing archive, attempt, sweep, and session changes. Require one approval and roll all protected files back if any grouped write fails.
