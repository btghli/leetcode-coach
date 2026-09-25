"""Normalize provider/UI message content before workflow interpretation."""

from __future__ import annotations

import re
from typing import Any


def normalize_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
            else:
                text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
        return "".join(parts)
    if content is None:
        return ""
    return str(content)


def is_accepted_report(text: str) -> bool:
    """Recognize an explicit accepted judge report in the current learner event."""

    normalized = " ".join(text.lower().strip().split())
    if any(token in normalized for token in (
        "没 ac", "没有 ac", "未 ac", "没过", "未通过", "not ac", "didn't get ac", "did not get ac",
    )):
        return False
    if normalized in {"/ac", "ac", "ac 了", "ac了", "提交通过", "提交通过了", "过了"}:
        return True
    if re.match(r"^/ac(?:$|\s|[：:，,。.!！])", normalized):
        return True
    if re.fullmatch(r"#?\d+\s*ac\s*(了|通过)?[。.!！]?", normalized):
        return True
    if re.search(r"\b(?:got|received|earned)\s+ac\b", normalized):
        return True
    if re.search(r"(?:\bno\.?\s*|\bnumber\s*|#)\d+.*\bac\b", normalized):
        return True
    return "ac" in normalized and any(token in normalized for token in ("通过了", "accepted"))


__all__ = ["is_accepted_report", "normalize_message_content"]
