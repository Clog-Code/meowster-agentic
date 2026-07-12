"""Utilities for converting between AG-UI messages and LangChain messages."""

import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


def to_lc_messages(ag_ui_messages, state: object | None = None) -> list:
    """Convert ag_ui Message objects to LangChain message objects.

    If *state* is provided, its items are prepended to the first human
    message so the agent always has owner/profile state available without
    touching the system prompt.
    """
    result = []
    state_prefix = _build_state_prefix(state) if state is not None else ""
    for m in ag_ui_messages:
        role = getattr(m, "role", None)
        content = getattr(m, "content", "") or ""

        if role == "user":
            if state_prefix and not result:  # inject once, into first user msg
                content = f"{state_prefix}\n\n{content}" if content else state_prefix
                state_prefix = ""  # consumed
            result.append(HumanMessage(content=content))

        elif role == "assistant":
            tool_calls = getattr(m, "tool_calls", None)
            if tool_calls:
                result.append(
                    AIMessage(
                        content=content,
                        tool_calls=[
                            {
                                "id": tc.id,
                                "name": tc.function.name,
                                "args": _safe_json_loads(tc.function.arguments),
                            }
                            for tc in tool_calls
                        ],
                    )
                )
            else:
                result.append(AIMessage(content=content))

        elif role == "tool":
            tool_call_id = getattr(m, "tool_call_id", "")
            result.append(ToolMessage(content=content, tool_call_id=tool_call_id))

        # system messages are skipped — the system prompt is injected
        # directly into the agent at build time instead.

    return result


def _safe_json_loads(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except json.JSONDecodeError:
        return {}


def _build_state_prefix(state: object) -> str:
    """Render AG-UI state items as a compact block for the agent."""
    if isinstance(state, dict):
        state_dict = state
    else:
        candidate = getattr(state, "__dict__", None)
        if not isinstance(candidate, dict):
            return ""
        state_dict = candidate

    lines = ["[state]"]
    for key, value in state_dict.items():
        if value is None:
            continue
        lines.append(f"{key}: {json.dumps(value, default=_json_default)}")
    return "\n".join(lines) if len(lines) > 1 else ""


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
