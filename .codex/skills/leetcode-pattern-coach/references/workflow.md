# Direct Pattern Coaching Workflow

Use these commands from the repository root. This workflow deliberately bypasses LangChain and LangGraph.

## Inspect curriculum

```bash
python3 .codex/skills/leetcode-pattern-coach/scripts/pattern_coach.py --root . status
python3 .codex/skills/leetcode-pattern-coach/scripts/pattern_coach.py --root . next
```

`next` returns JSON containing category, subpattern, representative problem, pattern card path, initialization status, and whether the category card should be shown.

To honor an explicit category request:

```bash
python3 .codex/skills/leetcode-pattern-coach/scripts/pattern_coach.py \
  --root . next --category graph
```

Only after the learner accepts the category/problem:

```bash
python3 .codex/skills/leetcode-pattern-coach/scripts/pattern_coach.py \
  --root . next --category graph --set-focus
```

## Initialize a catalog problem

Use the exact `problem` fields returned by `next`:

```bash
python3 .codex/skills/leetcode-coach/scripts/study.py init-problem \
  --root . \
  --id 200 \
  --slug number-of-islands \
  --title "Number of Islands" \
  --difficulty Medium \
  --status Doing \
  --json
```

Do not use `--force` on an existing problem. Preserve existing notes and solutions.

## During the attempt

Track these values in the conversation:

- training mode: normally `guided-solve`; use `blind-solve`, `pattern-contrast`, `debug-drill`, or `redo-from-memory` only when appropriate;
- highest hint level reached, 0–4;
- elapsed solve time if known;
- first-try AC;
- judge failures such as `WA,TLE`;
- standardized mistake tags from `knowledge/mistake-taxonomy.md`.

Update only user-confirmed observations in the problem note. Keep the note sections focused on restatement, invariant, approach, complexity, Teach-back, mistakes, pattern, and review log.

## After AC and Teach-back

Archive the learner's actual accepted solution. Prefer the VS Code plugin source when available:

```bash
python3 .codex/skills/leetcode-coach/scripts/study.py plugin-files --root . --slug number-of-islands
python3 .codex/skills/leetcode-coach/scripts/study.py archive-solution \
  --root . --slug number-of-islands --from-plugin --mode standalone --with-tests
```

If the learner supplies another local source path, use `--source <path>` instead. Never fabricate an accepted solution for archival.

Choose mastery from evidence:

- `shaky`: required substantial help or cannot explain the invariant/boundary reliably;
- `ok`: solved with limited help and completed Teach-back;
- `solid`: independent solution plus complete, precise Teach-back; never infer this from AC alone.

Then persist the attempt:

```bash
python3 .codex/skills/leetcode-coach/scripts/study.py finish \
  --root . \
  --slug number-of-islands \
  --status AC \
  --mastery ok \
  --mode guided-solve \
  --quality 4 \
  --hint-level 1 \
  --solve-minutes 25 \
  --first-try-ac false \
  --judge-failures "WA" \
  --mistake-tags "visited-timing" \
  --teach-back true \
  --json
```

Omit unknown optional flags rather than inventing values.

Sync generated curriculum views only through the deterministic helper:

```bash
python3 .codex/skills/leetcode-pattern-sweep/scripts/sweep.py --root . sync
python3 .codex/skills/leetcode-pattern-sweep/scripts/sweep.py --root . check
python3 .codex/skills/leetcode-coach/scripts/study.py --root . check
```

Optionally log a completed session:

```bash
python3 .codex/skills/leetcode-coach/scripts/study.py log-session \
  --root . \
  --problems number-of-islands \
  --summary "Completed graph traversal anchor and Teach-back." \
  --next "Continue the next uncovered graph subpattern." \
  --mode guided-solve \
  --quality 4 \
  --json
```

Only report completion after archive, finish, sync, and validation commands that were required for the attempt have succeeded.

