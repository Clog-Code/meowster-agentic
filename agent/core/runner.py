"""
Orchestrator builder + AG-UI streaming runner.

`get_or_build_agent()` assembles a single `create_deep_agent` instance:
native tools + every MCP-discovered tool, the three Module 2 subagents
(vet-emergency, supply-inventory, pet-info-lookup), and the skills
directory. It's built once (async, since MCP discovery is async) and
reused across requests.

`run_agent()` takes an AG-UI `RunAgentInput`, feeds it through the agent,
and yields AG-UI SSE strings — the same event vocabulary your prior
downtime-agent project used, so any AG-UI-compatible client (this repo's
`static/` test page, or the Flutter app) can consume it without change.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Any, cast

from ag_ui.core import RunAgentInput
from deepagents import create_deep_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver

from backend.services import persist_message

from ..backends import build_skills_backend
from ..config import LLM_DEFAULTS, MODE_INSTRUCT, MODE_THINKING_GENERAL
from ..filesystem import (
    build_subagent_configs,
    get_initializer_prompt,
    get_skills_virtual_path,
)
from ..llm import build_llm
from . import events as ev
from .messages import to_lc_messages
from .registry import build_tool_groups

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_chunk_text(chunk) -> str:
    """Normalise a LangChain stream chunk into plain text."""
    if chunk is None:
        return ""

    content = getattr(chunk, "content", chunk)
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)

    return ""


def _json_default(value):
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    to_dict = getattr(value, "dict", None)
    if callable(to_dict):
        return to_dict()
    content = getattr(value, "content", None)
    if content is not None:
        return {"type": value.__class__.__name__, "content": content}
    return str(value)


def _to_json_string(value) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, default=_json_default)


def _extract_todos_from_state(state: object) -> list[dict[str, object]]:
    if isinstance(state, dict):
        state_dict = state
    else:
        candidate = getattr(state, "values", None)
        if not isinstance(candidate, dict):
            return []
        state_dict = candidate

    raw_todos = state_dict.get("todos", [])
    if not isinstance(raw_todos, list):
        return []

    todos: list[dict[str, object]] = []
    for idx, todo in enumerate(raw_todos):
        todo_dict = todo if isinstance(todo, dict) else getattr(todo, "__dict__", {})
        todos.append(
            {
                "id": todo_dict.get("id") or f"todo-{idx}",
                "content": todo_dict.get("content") or "",
                "status": todo_dict.get("status") or "pending",
            }
        )
    return todos


# ---------------------------------------------------------------------------
# Agent singleton — built once, reused across requests
# ---------------------------------------------------------------------------

_AGENT: Any = None
_AGENT_LOCK = asyncio.Lock()

VALID_MODES = {
    "thinking_general": MODE_THINKING_GENERAL,
    "instruct": MODE_INSTRUCT,
}
DEFAULT_MODE = "thinking_general"


async def build_deep_agent(mode_config: dict | None = None, extra_tools=None):
    """Build a fresh create_deep_agent instance (async: MCP discovery + tool groups)."""
    tool_groups = await build_tool_groups(extra_tools)
    all_tools = [tool for tools in tool_groups.values() for tool in tools]
    tool_docs = (
        "\n".join(f"- {t.name}: {t.description}" for t in all_tools)
        or "(none discovered)"
    )

    subagent_configs = build_subagent_configs(tool_groups)

    backend = build_skills_backend()
    skill_source = get_skills_virtual_path()

    llm = build_llm(mode_config=mode_config or VALID_MODES[DEFAULT_MODE])

    return create_deep_agent(
        tools=all_tools,
        system_prompt=get_initializer_prompt(tool_docs),
        model=cast(BaseChatModel, llm),
        backend=backend,
        skills=[skill_source],
        checkpointer=MemorySaver(),
        subagents=cast(Any, subagent_configs),
    )


async def get_or_build_agent(mode: str = DEFAULT_MODE):
    """Return the cached agent, building it (with a lock) on first use."""
    global _AGENT  # pylint: disable=global-statement
    if _AGENT is not None:
        return _AGENT

    async with _AGENT_LOCK:
        if _AGENT is None:
            _AGENT = await build_deep_agent(mode_config=VALID_MODES.get(mode))
        return _AGENT


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def run_agent(  # pylint: disable=too-many-locals
    body: RunAgentInput, agent=None
) -> AsyncIterator[str]:
    """Receive a RunAgentInput, run the agentic loop, yield AG-UI SSE strings."""
    thread_id = body.thread_id
    run_id = body.run_id

    if agent is None:
        try:
            agent = await get_or_build_agent()
        except Exception as exc:
            yield ev.run_error(f"Failed to initialise agent: {exc}")
            return

    yield ev.run_started(thread_id, run_id)

    current_text_message_id: str | None = None
    last_state_snapshot: str | None = None
    assistant_content_parts: list[str] = []

    config: RunnableConfig = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": LLM_DEFAULTS["recursion_limit"],
    }

    async def emit_state_snapshot() -> str | None:
        nonlocal last_state_snapshot
        try:
            state = await agent.aget_state(config)
        except Exception:
            return None

        todos = _extract_todos_from_state(state)
        snapshot_payload = {"todos": todos}
        snapshot_key = json.dumps(
            snapshot_payload, sort_keys=True, default=_json_default
        )
        if snapshot_key == last_state_snapshot:
            return None

        last_state_snapshot = snapshot_key
        return ev.state_snapshot(snapshot_payload)

    try:
        messages = to_lc_messages(body.messages)

        async for event in agent.astream_events(
            {"messages": messages}, config=config, version="v2"
        ):
            kind = event.get("event", "")
            data = event.get("data", {})

            if kind == "on_chat_model_stream":
                chunk = data.get("chunk")
                text_delta = _extract_chunk_text(chunk)
                if text_delta:
                    if current_text_message_id is None:
                        current_text_message_id = str(uuid.uuid4())
                        yield ev.text_start(current_text_message_id)
                    yield ev.text_delta(current_text_message_id, text_delta)
                    assistant_content_parts.append(text_delta)

            elif kind == "on_chat_model_end":
                if current_text_message_id is not None:
                    yield ev.text_end(current_text_message_id)
                    current_text_message_id = None

                snapshot_event = await emit_state_snapshot()
                if snapshot_event is not None:
                    yield snapshot_event

            elif kind == "on_tool_start":
                call_id = event.get("run_id") or str(uuid.uuid4())
                tool_name = event.get("name", "unknown_tool")
                raw_args = _to_json_string(data.get("input", {}))

                if current_text_message_id is None:
                    current_text_message_id = str(uuid.uuid4())
                    yield ev.text_start(current_text_message_id)

                yield ev.tool_start(call_id, tool_name, current_text_message_id)
                for chunk_str in ev.tool_args_chunks(call_id, raw_args):
                    yield chunk_str
                yield ev.tool_end(call_id)

            elif kind == "on_tool_end":
                call_id = event.get("run_id") or str(uuid.uuid4())
                result_str = _to_json_string(data.get("output", ""))
                yield ev.tool_result(str(uuid.uuid4()), call_id, result_str)

                snapshot_event = await emit_state_snapshot()
                if snapshot_event is not None:
                    yield snapshot_event

        if current_text_message_id is not None:
            yield ev.text_end(current_text_message_id)

        snapshot_event = await emit_state_snapshot()
        if snapshot_event is not None:
            yield snapshot_event

    except Exception as exc:
        yield ev.run_error(str(exc))
        return

    assistant_content = "".join(assistant_content_parts).strip()
    if assistant_content:
        try:
            persist_message(
                str(uuid.uuid4()), thread_id, "assistant", assistant_content
            )
        except Exception:
            pass

    yield ev.run_finished(thread_id, run_id)
