PYTHON ?= python3

.PHONY: check test ui agent-server strict-check migrate-preview migrate

check:
	$(PYTHON) -m py_compile .codex/skills/leetcode-coach/scripts/study.py
	$(PYTHON) -m py_compile .codex/skills/leetcode-pattern-coach/scripts/pattern_coach.py
	$(PYTHON) -m py_compile .codex/skills/leetcode-pattern-sweep/scripts/sweep.py
	$(PYTHON) .codex/skills/leetcode-coach/scripts/study.py check
	$(PYTHON) .codex/skills/leetcode-pattern-sweep/scripts/sweep.py --root . check

test:
	$(PYTHON) -m pytest

ui:
	.venv/bin/leetcode-coach-ui

agent-server:
	.venv/bin/langgraph dev --no-browser --port 2024

strict-check:
	$(PYTHON) -m py_compile .codex/skills/leetcode-coach/scripts/study.py
	$(PYTHON) -m py_compile .codex/skills/leetcode-pattern-coach/scripts/pattern_coach.py
	$(PYTHON) -m py_compile .codex/skills/leetcode-pattern-sweep/scripts/sweep.py
	$(PYTHON) .codex/skills/leetcode-coach/scripts/study.py check --strict
	$(PYTHON) .codex/skills/leetcode-pattern-sweep/scripts/sweep.py --root . check

migrate-preview:
	$(PYTHON) .codex/skills/leetcode-coach/scripts/study.py migrate

migrate:
	$(PYTHON) .codex/skills/leetcode-coach/scripts/study.py migrate --write
