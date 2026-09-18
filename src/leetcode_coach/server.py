"""Agent Server export consumed by ``langgraph dev`` and Agent Chat UI."""

from __future__ import annotations

from pathlib import Path

from .config import load_config
from .engines import build_decision_engine
from .graph import TrainingGraph
from .services import MetadataResolver, PatternSweepService, StudyService, find_root


def create_graph(root: Path | None = None):
    """Build a server-managed graph without embedding a local checkpointer."""
    project_root = find_root(root or Path.cwd())
    config = load_config(project_root)
    study = StudyService(project_root)
    sweep = PatternSweepService(project_root)
    resolver = MetadataResolver(study, sweep, config.mcp)
    engine = build_decision_engine(config, study, sweep)
    return TrainingGraph(study, sweep, resolver, engine).build()


# Agent Server injects its own checkpointer and thread persistence.
graph = create_graph()


__all__ = ["create_graph", "graph"]
