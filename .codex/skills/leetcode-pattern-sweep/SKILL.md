---
name: leetcode-pattern-sweep
description: Route new LeetCode practice by pattern curriculum through the shared LangGraph coach. Use when the user starts, continues, inspects, or updates a pattern sweep; asks what new pattern to study next; or wants to advance uncovered subpatterns without reviews.
---

# LeetCode Pattern Sweep

Use the canonical runtime:

```bash
leetcode-coach status --brief
leetcode-coach sweep status
leetcode-coach sweep next
leetcode-coach chat --engine codex-cli --thread-id <stable-id>
```

Pattern sweep is a separate new-curriculum lane. Do not route due reviews, current Doing/Review problems, or active-list fallback while it is active. Continue the current started pattern until that entire category is complete. Only when choosing a new category, select the first wholly untouched pattern; after all categories have been started, return to any remaining partially covered category. Show a newly selected pattern's card and pause before starting its first uncovered subpattern; then complete uncovered representative problems one at a time in catalog order. Delegate per-problem coaching and persistence to the shared training graph.

Do not advance merely because assistant prose says a subpattern is complete. Require a complete structured teach-back assessment, approved attempt persistence, and successful sweep sync before selecting the next subpattern.

Keep `study/pattern-sweep.json` authoritative for curriculum and focus. Keep `problems/**/note.md` authoritative for learning evidence. Do not hand-edit generated sweep-map regions; sync them only through the reviewed graph action or `leetcode-coach sweep sync`.

Read [docs/agent-workflow.md](../../../docs/agent-workflow.md) for the shared workflow.
