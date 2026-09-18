"""Unified local CLI for deterministic commands and the LangGraph chat loop."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain.messages import AIMessage, HumanMessage
from langgraph.types import Command

from .config import load_config
from .engines import build_decision_engine
from .graph import TrainingGraph
from .services import MetadataResolver, PatternSweepService, StudyService, find_root


def _json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _build_services(
    root: Path,
    model_name: str | None = None,
    engine_name: str | None = None,
    codex_model: str | None = None,
):
    config = load_config(root, model_name, engine_name, codex_model)
    study, sweep = StudyService(root), PatternSweepService(root)
    resolver = MetadataResolver(study, sweep, config.mcp)
    return config, study, sweep, resolver


def _value(output: Any) -> dict[str, Any]:
    value = getattr(output, "value", output)
    return value if isinstance(value, dict) else {}


def _interrupts(output: Any) -> tuple[Any, ...]:
    interrupts = getattr(output, "interrupts", ())
    if interrupts:
        return tuple(interrupts)
    value = _value(output)
    legacy = value.get("__interrupt__", ())
    return tuple(legacy) if legacy else ()


@dataclass
class StreamOutput:
    value: dict[str, Any]
    interrupts: tuple[Any, ...] = ()


async def _stream_graph(graph: Any, graph_input: Any, run_config: dict[str, Any]) -> StreamOutput:
    value: dict[str, Any] = {}
    interruptions: tuple[Any, ...] = ()
    wrote_token = False
    async for part in graph.astream(
        graph_input,
        config=run_config,
        stream_mode=["messages", "updates", "values"],
        version="v2",
    ):
        kind = part.get("type")
        if kind == "messages":
            message, metadata = part.get("data", (None, {}))
            content = getattr(message, "content", "")
            if content and metadata.get("langgraph_node") == "model":
                if not wrote_token:
                    print("Coach: ", end="", flush=True)
                    wrote_token = True
                print(content, end="", flush=True)
        elif kind == "updates":
            nodes = [name for name in part.get("data", {}) if not name.startswith("__")]
            if nodes:
                print(f"\n[stage: {', '.join(nodes)}]")
        elif kind == "values":
            data = part.get("data")
            if isinstance(data, dict):
                value = data
            interruptions = tuple(part.get("interrupts") or ())
    if wrote_token:
        print()
    return StreamOutput(value=value, interrupts=interruptions)


def _print_new_messages(state: dict[str, Any], seen: set[str]) -> None:
    for message in state.get("messages", []):
        identifier = getattr(message, "id", None) or str(id(message))
        if identifier in seen:
            continue
        seen.add(identifier)
        if isinstance(message, AIMessage) and message.content:
            print(f"Coach: {message.content}")


async def _approval_payload(output: Any) -> dict[str, Any]:
    item = _interrupts(output)[0]
    value = getattr(item, "value", item)
    return value if isinstance(value, dict) else {"description": str(value), "arguments": {}}


async def _ask_approval(output: Any) -> dict[str, Any]:
    pending = await _approval_payload(output)
    print("\nPending write:")
    _json(pending)
    while True:
        choice = input("Approve, edit, or reject? [a/e/r] ").strip().lower()
        if choice in {"a", "approve"}:
            return {"type": "approve"}
        if choice in {"r", "reject"}:
            return {"type": "reject"}
        if choice in {"e", "edit"}:
            raw = input("Replacement arguments as JSON: ").strip()
            try:
                arguments = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(f"Invalid JSON: {exc}")
                continue
            if not isinstance(arguments, dict):
                print("Arguments must be a JSON object.")
                continue
            return {"type": "edit", "arguments": arguments}


async def run_chat(
    root: Path,
    model_name: str | None,
    thread_id: str | None,
    engine_name: str | None = None,
    codex_model: str | None = None,
) -> int:
    # Preserve the historical contract: an explicit provider model selects LangChain.
    selected_engine = engine_name or ("langchain" if model_name else None)
    config, study, sweep, resolver = _build_services(root, model_name, selected_engine, codex_model)
    engine = build_decision_engine(config, study, sweep)
    checkpoint_path = config.resolved_checkpoint_path
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    thread_id = thread_id or f"session-{uuid.uuid4().hex[:10]}"
    run_config = {"configurable": {"thread_id": thread_id}}
    seen: set[str] = set()

    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    print(f"Thread: {thread_id}")
    async with AsyncSqliteSaver.from_conn_string(str(checkpoint_path)) as saver:
        graph = TrainingGraph(study, sweep, resolver, engine).build(checkpointer=saver)
        output = await _stream_graph(graph, {"messages": [], "thread_id": thread_id}, run_config)
        _print_new_messages(_value(output), seen)
        while _interrupts(output):
            decision = await _ask_approval(output)
            output = await _stream_graph(graph, Command(resume=decision), run_config)
            _print_new_messages(_value(output), seen)

        while _value(output).get("phase") != "complete":
            try:
                text = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nConversation checkpoint preserved.")
                return 0
            if not text:
                continue
            output = await _stream_graph(graph, {"messages": [HumanMessage(content=text)]}, run_config)
            _print_new_messages(_value(output), seen)
            while _interrupts(output):
                decision = await _ask_approval(output)
                output = await _stream_graph(graph, Command(resume=decision), run_config)
                _print_new_messages(_value(output), seen)
    return 0


async def list_threads(path: Path) -> int:
    if not path.exists():
        print("No saved threads.")
        return 0
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    found: set[str] = set()
    async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
        async for checkpoint in saver.alist(None):
            thread = checkpoint.config.get("configurable", {}).get("thread_id")
            if thread:
                found.add(str(thread))
    for thread in sorted(found):
        print(thread)
    return 0


async def delete_thread(path: Path, thread_id: str) -> int:
    if not path.exists():
        print("No checkpoint database found.", file=sys.stderr)
        return 2
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
        await saver.adelete_thread(thread_id)
    print(f"Deleted thread: {thread_id}")
    return 0


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(prog="leetcode-coach")
    command.add_argument("--root", type=Path)
    sub = command.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("--brief", action="store_true")
    sub.add_parser("plan")
    sweep = sub.add_parser("sweep")
    sweep.add_argument("action", choices=["status", "next", "sync"], default="status", nargs="?")
    chat = sub.add_parser("chat")
    chat.add_argument("--engine", choices=["codex-cli", "langchain"])
    chat.add_argument("--model")
    chat.add_argument("--codex-model")
    chat.add_argument("--thread-id")
    threads = sub.add_parser("threads")
    threads_sub = threads.add_subparsers(dest="threads_command", required=True)
    threads_sub.add_parser("list")
    delete = threads_sub.add_parser("delete")
    delete.add_argument("thread_id")
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        root = (args.root.resolve() if args.root else find_root())
        config, study, sweep, _ = _build_services(root, getattr(args, "model", None))
        if args.command == "status":
            if args.brief:
                print(study.scheduler.status_brief())
            else:
                _json(study.status())
            return 0
        if args.command == "plan":
            _json(study.plan_day())
            return 0
        if args.command == "sweep":
            if args.action == "status":
                _json(sweep.status())
            elif args.action == "next":
                _json(sweep.recommend_next())
            else:
                _json(sweep.sync())
            return 0
        if args.command == "chat":
            return asyncio.run(run_chat(root, args.model, args.thread_id, args.engine, args.codex_model))
        if args.command == "threads":
            if args.threads_command == "list":
                return asyncio.run(list_threads(config.resolved_checkpoint_path))
            return asyncio.run(delete_thread(config.resolved_checkpoint_path, args.thread_id))
        return 2
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
