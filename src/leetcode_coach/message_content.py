"""Normalize provider/UI message content before workflow interpretation."""

from __future__ import annotations

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


__all__ = ["normalize_message_content"]
