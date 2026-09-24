#!/usr/bin/env python3
"""Compatibility wrapper for the canonical application study store."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from leetcode_coach.study_store import *  # noqa: F403,E402
from leetcode_coach.study_store import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
