"""
AG-UI event helpers.

Thin wrappers around `ag_ui.core` event models + `ag_ui.encoder.EventEncoder`
so the runner can emit spec-compliant SSE without repeating boilerplate.
Any AG-UI-compatible frontend (a browser test page, or a Flutter app using
an SSE client) can consume these directly.
"""

from datetime import UTC, datetime

from ag_ui.core import (
    EventType,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StateSnapshotEvent,
    StepFinishedEvent,
    StepStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from ag_ui.encoder import EventEncoder

_encoder = EventEncoder()

TEXT_CHUNK = 30
ARGS_CHUNK = 40


def _now() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def sse(event) -> str:
    """Convert an event object to a Server-Sent Event (SSE) string."""
    return _encoder.encode(event)


# ── lifecycle ────────────────────────────────────────────────────────────────


def run_started(thread_id, run_id) -> str:
    """Build a run-started SSE event."""
    return sse(
        RunStartedEvent(
            type=EventType.RUN_STARTED,
            timestamp=_now(),
            thread_id=thread_id,
            run_id=run_id,
        )
    )


def run_finished(thread_id, run_id) -> str:
    """Build a run-finished SSE event."""
    return sse(
        RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            timestamp=_now(),
            thread_id=thread_id,
            run_id=run_id,
        )
    )


def run_error(message: str) -> str:
    """Build a run-error SSE event."""
    return sse(
        RunErrorEvent(type=EventType.RUN_ERROR, timestamp=_now(), message=message)
    )


def step_started(name: str) -> str:
    """Build a step-started SSE event."""
    return sse(
        StepStartedEvent(type=EventType.STEP_STARTED, timestamp=_now(), step_name=name)
    )


def step_finished(name: str) -> str:
    """Build a step-finished SSE event."""
    return sse(
        StepFinishedEvent(
            type=EventType.STEP_FINISHED, timestamp=_now(), step_name=name
        )
    )


# ── text streaming ───────────────────────────────────────────────────────────


def text_start(msg_id: str) -> str:
    """Build a text-message-start SSE event."""
    return sse(
        TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            timestamp=_now(),
            message_id=msg_id,
            role="assistant",
        )
    )


def text_delta(msg_id: str, delta: str) -> str:
    """Build a text-message-content SSE event."""
    return sse(
        TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            timestamp=_now(),
            message_id=msg_id,
            delta=delta,
        )
    )


def text_end(msg_id: str) -> str:
    """Build a text-message-end SSE event."""
    return sse(
        TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END, timestamp=_now(), message_id=msg_id
        )
    )


# ── tool call streaming ──────────────────────────────────────────────────────


def tool_start(call_id: str, name: str, parent_msg_id: str) -> str:
    """Build a tool-call-start SSE event."""
    return sse(
        ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            timestamp=_now(),
            tool_call_id=call_id,
            tool_call_name=name,
            parent_message_id=parent_msg_id,
        )
    )


def tool_args_chunks(call_id: str, raw_args: str) -> list[str]:
    """Build tool-call-args chunk SSE events (split for streaming)."""
    return [
        sse(
            ToolCallArgsEvent(
                type=EventType.TOOL_CALL_ARGS,
                timestamp=_now(),
                tool_call_id=call_id,
                delta=raw_args[i : i + ARGS_CHUNK],
            )
        )
        for i in range(0, len(raw_args), ARGS_CHUNK)
    ] or [
        sse(
            ToolCallArgsEvent(
                type=EventType.TOOL_CALL_ARGS,
                timestamp=_now(),
                tool_call_id=call_id,
                delta="",
            )
        )
    ]


def tool_end(call_id: str) -> str:
    """Build a tool-call-end SSE event."""
    return sse(
        ToolCallEndEvent(
            type=EventType.TOOL_CALL_END, timestamp=_now(), tool_call_id=call_id
        )
    )


def tool_result(msg_id: str, call_id: str, content: str) -> str:
    """Build a tool-call-result SSE event."""
    return sse(
        ToolCallResultEvent(
            type=EventType.TOOL_CALL_RESULT,
            timestamp=_now(),
            message_id=msg_id,
            tool_call_id=call_id,
            content=content,
            role="tool",
        )
    )


# ── state ────────────────────────────────────────────────────────────────────


def state_snapshot(snapshot: dict) -> str:
    """Build a state-snapshot SSE event."""
    return sse(
        StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT, timestamp=_now(), snapshot=snapshot
        )
    )
