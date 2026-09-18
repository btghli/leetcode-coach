"""Project configuration and provider-safe model initialization."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AppConfig:
    root: Path
    engine: str = "codex-cli"
    model: str | None = None
    codex_model: str | None = None
    codex_bin: str | None = None
    codex_timeout_seconds: float = 120.0
    checkpoint_path: Path | None = None
    mcp: dict[str, Any] = field(default_factory=dict)

    @property
    def resolved_checkpoint_path(self) -> Path:
        return self.checkpoint_path or self.root / ".cache" / "leetcode-coach" / "checkpoints.sqlite"


def load_config(
    root: Path,
    model_override: str | None = None,
    engine_override: str | None = None,
    codex_model_override: str | None = None,
) -> AppConfig:
    path = root / "leetcode-coach.toml"
    raw: dict[str, Any] = {}
    if path.exists():
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    configured_model = raw.get("model") if isinstance(raw.get("model"), str) else None
    model = model_override or os.getenv("LEETCODE_COACH_MODEL") or configured_model
    configured_engine = raw.get("engine") if isinstance(raw.get("engine"), str) else None
    engine = engine_override or os.getenv("LEETCODE_COACH_ENGINE") or configured_engine or "codex-cli"
    if engine not in {"codex-cli", "langchain"}:
        raise ValueError("engine must be 'codex-cli' or 'langchain'.")
    configured_codex_model = raw.get("codex_model") if isinstance(raw.get("codex_model"), str) else None
    codex_model = codex_model_override or os.getenv("LEETCODE_COACH_CODEX_MODEL") or configured_codex_model
    configured_codex_bin = raw.get("codex_bin") if isinstance(raw.get("codex_bin"), str) else None
    codex_bin = os.getenv("LEETCODE_COACH_CODEX_BIN") or configured_codex_bin
    configured_timeout = raw.get("codex_timeout_seconds", 120.0)
    timeout_raw = os.getenv("LEETCODE_COACH_CODEX_TIMEOUT") or configured_timeout
    try:
        codex_timeout_seconds = float(timeout_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("codex_timeout_seconds must be a number.") from exc
    if codex_timeout_seconds <= 0:
        raise ValueError("codex_timeout_seconds must be greater than zero.")
    checkpoint = raw.get("checkpoint_path")
    checkpoint_path = (root / checkpoint).resolve() if isinstance(checkpoint, str) else None
    mcp = raw.get("mcp") if isinstance(raw.get("mcp"), dict) else {}
    return AppConfig(
        root=root.resolve(),
        engine=engine,
        model=model,
        codex_model=codex_model,
        codex_bin=codex_bin,
        codex_timeout_seconds=codex_timeout_seconds,
        checkpoint_path=checkpoint_path,
        mcp=mcp,
    )


def initialize_model(model_name: str | None):
    if not model_name:
        raise ValueError("No model configured. Pass --model or set LEETCODE_COACH_MODEL.")
    provider = model_name.split(":", 1)[0] if ":" in model_name else ""
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is not configured for the selected OpenAI model.")
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY is not configured for the selected Anthropic model.")
    from langchain.chat_models import init_chat_model

    return init_chat_model(model_name, temperature=0)
