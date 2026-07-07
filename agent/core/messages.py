"""Utilities for converting between AG-UI messages and LangChain messages."""

import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


def to_lc_messages(ag_ui_messages) -> list:
    """Convert ag_ui Message objects to LangChain message objects."""
    result = []
    for m in ag_ui_messages:
        role = getattr(m, "role", None)
        content = getattr(m, "content", "") or ""

        if role == "user":
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
