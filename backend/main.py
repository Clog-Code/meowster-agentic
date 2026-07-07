"""
Single FastAPI service for Module 2 (Autonomous Intervention).

Routes:
  POST /agent        AG-UI run endpoint. Body is an AG-UI RunAgentInput
                      (thread_id, run_id, messages, ...). Streams back
                      AG-UI SSE events. This is what the Flutter app (or
                      the /static test page) talks to.

  POST /perception    Webhook the ML teammate's module (Module 1) calls
                      with a structured JSON summary of what it detected.
                      Internally converts it into an AG-UI run and streams
                      the same SSE event vocabulary back, so it can be
                      called either fire-and-forget or relayed onward to a
                      live frontend connection.

  GET  /healthz       Liveness check.
  GET  /              Serves the static AG-UI test page.

MCP servers are self-discovered from .env (see agent/mcp/config.py) the
first time the agent is built — no code changes needed to add a new plugin.
"""

from __future__ import annotations

import uuid

from dotenv import load_dotenv
from ag_ui.core import RunAgentInput
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Load .env before any local config so LANGSMITH_*, DATABASE_PATH,
# MCP_SERVERS, and other env‑based settings are available.
load_dotenv()

from agent.core import parse_perception_payload, run_agent  # noqa: E402  # pylint: disable=wrong-import-position

from .config import BASE_DIR, CORS_ALLOW_ORIGINS, PERCEPTION_INGEST_TOKEN  # noqa: E402  # pylint: disable=wrong-import-position
from .db import init_db  # noqa: E402  # pylint: disable=wrong-import-position
from .services import ensure_thread, record_perception_event  # noqa: E402  # pylint: disable=wrong-import-position

app = FastAPI(title="Pet Companion — Module 2 (Autonomous Intervention)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


# ---------------------------------------------------------------------------
# AG-UI run endpoint
# ---------------------------------------------------------------------------


@app.post("/agent")
async def agent_run(request: Request):
    """AG-UI run endpoint: accepts a RunAgentInput, streams AG-UI SSE events."""
    raw_body = await request.json()
    body = RunAgentInput.model_validate(raw_body)
    ensure_thread(body.thread_id)

    return StreamingResponse(
        run_agent(body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Perception webhook (Module 1 -> Module 2)
# ---------------------------------------------------------------------------


class PerceptionPayload(BaseModel):
    """Wire format for the Module-1 perception webhook payload."""

    pet_id: str
    species: str
    emotion: str | None = None
    emotion_confidence: float | None = None
    health_flags: list[str] = []
    food_level: str | None = None
    water_level: str | None = None
    notes: str | None = None
    timestamp: str | None = None
    thread_id: str | None = None  # reuse an existing conversation if provided


@app.post("/perception")
async def perception_webhook(
    payload: PerceptionPayload,
    authorization: str | None = Header(default=None),
):
    """
    Ingest a perception event from Module 1's ML pipeline, convert it into
    an AG-UI run, and stream back the same SSE event vocabulary as /agent.
    """
    if PERCEPTION_INGEST_TOKEN:
        expected = f"Bearer {PERCEPTION_INGEST_TOKEN}"
        if authorization != expected:
            raise HTTPException(
                status_code=401, detail="Invalid or missing perception token."
            )

    event = parse_perception_payload(payload.model_dump())
    workflow = event.classify()
    thread_id = payload.thread_id or str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    ensure_thread(thread_id)
    record_perception_event(
        event.pet_id, payload.model_dump(), workflow.value, thread_id
    )

    body = RunAgentInput.model_validate(
        {
            "thread_id": thread_id,
            "run_id": run_id,
            "state": {},
            "messages": [
                {
                    "id": str(uuid.uuid4()),
                    "role": "user",
                    "content": event.to_orchestrator_message(),
                }
            ],
            "tools": [],
            "context": [],
            "forwarded_props": {},
        }
    )

    return StreamingResponse(
        run_agent(body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Health check + static AG-UI test page
# ---------------------------------------------------------------------------


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


app.mount(
    "/", StaticFiles(directory=str(BASE_DIR / "static"), html=True), name="static"
)
