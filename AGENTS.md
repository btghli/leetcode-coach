# LeetCode Coach repository guidance

## Commands

- Install development dependencies: `python3 -m pip install -e '.[dev,openai,anthropic,mcp]'`
- Validate repository data: `make check`
- Run offline tests: `make test`
- Show study status: `leetcode-coach status --brief`
- Start the LangGraph coach with local Codex auth: `leetcode-coach chat --engine codex-cli`
- Use a LangChain provider explicitly: `leetcode-coach chat --engine langchain --model provider:model-id`

## Contracts

- Treat `problems/**/note.md` as the source of truth for per-problem progress.
- Treat `study/pattern-sweep.json` as the source of truth for curriculum coverage.
- Preserve user-authored solutions, notes, sessions, and pattern-card prose.
- Never mark mastery `solid` without completed teach-back evidence.
- Do not copy full official problem statements into the repository.
- Keep model calls out of deterministic scheduling, validation, and persistence rules.
- Keep LangGraph as the sole owner of conversation state and checkpoints; decision engines return only validated `TurnDecision` values.

## Verification

- Run `make check` after repository-data changes.
- Run `make test` after Python, CLI, tool, or graph changes.
- Automated tests must not require API keys or live MCP servers.
