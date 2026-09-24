"""Opt-in, redacted LangSmith tracing; never owns learning state."""
from __future__ import annotations

import logging
import atexit
import os
import re
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from langchain_core.messages import BaseMessage
from langchain_core.tracers.langchain import LangChainTracer
from langsmith import Client, trace, tracing_context
from pydantic import BaseModel


def redact(value, secrets=()):
    """Defense in depth, not a guarantee that arbitrary personal data is removed."""
    if isinstance(value, BaseMessage):
        return redact({'type': value.type, 'content': value.content}, secrets)
    if isinstance(value, BaseModel):
        return redact(value.model_dump(), secrets)
    if is_dataclass(value) and not isinstance(value, type):
        return redact(asdict(value), secrets)
    if isinstance(value, dict):
        return {k: ('[REDACTED]' if re.search(r'api[_-]?key|password|secret|authorization|cookie', str(k), re.I)
                    else redact(v, secrets)) for k, v in value.items()
                if k not in {'serialized', 'runtime', 'attachments'}}
    if isinstance(value, (list, tuple)):
        return [redact(item, secrets) for item in value]
    if isinstance(value, Path):
        return '[LOCAL_PATH]'
    if isinstance(value, str):
        for secret in secrets:
            if secret and len(secret) >= 8:
                value = value.replace(secret, '[REDACTED]')
        value = re.sub(r'\b(?:sk-|lsv2_|ls__)[A-Za-z0-9_-]+', '[REDACTED]', value)
        value = re.sub(r'(?i)Bearer\s+[A-Za-z0-9._~-]+', 'Bearer [REDACTED]', value)
        value = re.sub(r'(?:/Users/|/home/|/private/|/var/|/tmp/)[^\s"\'<>]+', '[LOCAL_PATH]', value)
        return value
    return value


class RedactingClient(Client):
    """Filter every run envelope, including errors and metadata, before queueing."""
    def __init__(self, *, secrets=(), **kwargs):
        self._coach_secrets = secrets
        super().__init__(**kwargs)

    def create_run(self, *args, **kwargs):
        return super().create_run(*redact(args, self._coach_secrets), **redact(kwargs, self._coach_secrets))

    def update_run(self, *args, **kwargs):
        return super().update_run(*redact(args, self._coach_secrets), **redact(kwargs, self._coach_secrets))


class Observer:
    def __init__(self, client, project):
        self.client, self.project = client, project

    def callbacks(self):
        return [LangChainTracer(client=self.client, project_name=self.project, tags=['leetcode-coach'])]

    @contextmanager
    def llm(self, prompt, metadata):
        with tracing_context(enabled=True, client=self.client, project_name=self.project):
            with trace('codex.decision', run_type='llm', client=self.client,
                       project_name=self.project, inputs={'messages': [{'role': 'user', 'content': prompt}]},
                       metadata=metadata) as run:
                yield run


@lru_cache(maxsize=8)
def get_observer(root: Path):
    # Only tracing settings are consumed; do not change model authentication.
    local = dotenv_values(root / '.env.local', interpolate=False)
    settings = {**local, **os.environ}
    enabled = str(settings.get('LANGSMITH_TRACING', 'true')).lower() in {'true', '1'}
    key = settings.get('LANGSMITH_API_KEY')
    if not enabled or not key:
        return None
    secrets = tuple(str(v) for k, v in settings.items() if v and re.search(r'KEY|TOKEN|SECRET|PASSWORD', k))
    try:
        client = RedactingClient(
            api_key=key, api_url=settings.get('LANGSMITH_ENDPOINT') or 'https://api.smith.langchain.com',
            workspace_id=settings.get('LANGSMITH_WORKSPACE_ID') or None,
            secrets=secrets, omit_traced_runtime_info=True,
            timeout_ms=5000, tracing_sampling_rate=float(settings.get('LANGSMITH_TRACING_SAMPLING_RATE') or 1),
            tracing_error_callback=lambda exc: logging.warning('LangSmith upload failed (%s); coaching continues.', type(exc).__name__),
        )
        atexit.register(client.flush, timeout=5)
        return Observer(client, settings.get('LANGSMITH_PROJECT') or 'leetcode-coach')
    except Exception as exc:
        logging.warning('LangSmith disabled (%s); check tracing configuration.', type(exc).__name__)
        return None


def trace_config(root: Path):
    observer = get_observer(root)
    return {'callbacks': observer.callbacks()} if observer else {}
