"""Deterministic parsing for explicit learner workflow commands."""

from __future__ import annotations

from .message_content import is_accepted_report


def _normalized(text: str) -> str:
    return " ".join(text.lower().strip().split())


def routing_mode_command(text: str) -> str | None:
    normalized = _normalized(text)
    if normalized in {"/auto", "/mode auto", "/退出扫荡"}:
        return "auto"
    mentions_sweep = "扫荡" in normalized or "pattern-sweep" in normalized or "pattern sweep" in normalized
    if mentions_sweep and any(token in normalized for token in ("退出", "关闭", "停止", "离开")):
        return "auto"
    if "自动选题" in normalized and any(token in normalized for token in ("切换", "进入", "恢复", "使用")):
        return "auto"
    if normalized in {"/sweep", "/mode pattern-sweep"}:
        return "pattern-sweep"
    if mentions_sweep and any(token in normalized for token in ("切换", "进入", "开启", "开始", "启用", "使用", "我要")):
        return "pattern-sweep"
    return None


def next_subpattern_command(text: str) -> bool:
    normalized = _normalized(text)
    if normalized in {"/next-subpattern", "/next pattern"}:
        return True
    mentions_next = any(token in normalized for token in ("下一个", "继续下个", "next"))
    mentions_subpattern = any(token in normalized for token in ("小模式", "subpattern", "sub-pattern"))
    return mentions_next and mentions_subpattern


def next_problem_command(text: str) -> bool:
    return _normalized(text) in {"下一题", "继续下一题", "下道题", "next", "next problem", "/next"}


def accepted_command(text: str) -> bool:
    return is_accepted_report(text)


def approval_command(text: str) -> str | None:
    normalized = _normalized(text)
    if normalized in {"批准", "同意", "确认", "approve", "/approve", "批准并继续"}:
        return "approve"
    if normalized in {"拒绝", "不同意", "reject", "/reject", "不要保存"}:
        return "reject"
    return None


__all__ = [
    "accepted_command",
    "approval_command",
    "next_problem_command",
    "next_subpattern_command",
    "routing_mode_command",
]
