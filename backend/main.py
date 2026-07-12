"""
Single FastAPI service for Module 2 (Autonomous Intervention).

Routes:
  POST /agent               AG-UI run endpoint — accepts RunAgentInput,
                             streams AG-UI SSE events. Also persists every
                             incoming message to the DB.
  POST /perception           Webhook for the ML teammate's module (Module 1).
  GET  /threads              List recently active conversation threads.
  GET  /threads/{id}/messages  Full persisted message history for a thread.
  GET  /healthz              Liveness check.
  GET  /                     Serves the static AG-UI test page.

Sub-routers:
  /auth                      OAuth endpoints (see backend/api/auth.py).
"""

from __future__ import annotations

import uuid
from typing import Any

from dotenv import load_dotenv
from ag_ui.core import RunAgentInput
from fastapi import FastAPI, Header, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Load .env before any local config so LANGSMITH_*, DATABASE_PATH,
# MCP_SERVERS, and other env‑based settings are available.
load_dotenv()

from agent.core import parse_perception_payload, run_agent  # noqa: E402  # pylint: disable=wrong-import-position

from .api.auth import router as auth_router  # noqa: E402  # pylint: disable=wrong-import-position
from .config import BASE_DIR, CORS_ALLOW_ORIGINS, PERCEPTION_INGEST_TOKEN  # noqa: E402  # pylint: disable=wrong-import-position

UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
from .db import init_db  # noqa: E402  # pylint: disable=wrong-import-position
from .services import (  # noqa: E402  # pylint: disable=wrong-import-position
    ensure_thread,
    get_thread_messages,
    list_threads,
    persist_message,
    record_perception_event,
)

app = FastAPI(title="Pet Companion — Module 2 (Autonomous Intervention)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    UPLOADS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# File upload endpoint
# ---------------------------------------------------------------------------


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Save an uploaded image and return its URL and absolute disk path."""
    name = file.filename or "file"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else "bin"
    filename = f"{uuid.uuid4()}.{ext}"
    dest = UPLOADS_DIR / filename
    dest.write_bytes(await file.read())
    return JSONResponse(
        {
            "url": f"/uploads/{filename}",
            "path": str(dest.resolve()),
            "filename": file.filename,
        }
    )


# ---------------------------------------------------------------------------
# AG-UI run endpoint
# ---------------------------------------------------------------------------


@app.post("/agent")
async def agent_run(request: Request):
    """AG-UI run endpoint: accepts a RunAgentInput, streams AG-UI SSE events."""
    raw_body = await request.json()
    body = RunAgentInput.model_validate(raw_body)
    ensure_thread(body.thread_id)

    # The client (web test harness or Flutter app) re-sends its whole
    # rolling message history on every call, so persisting each message
    # here — keyed by its own client-assigned id — is idempotent (an
    # `INSERT OR REPLACE`, see backend/services.py) and means the
    # conversation is durable even if the stream below errors out before
    # the assistant's reply is generated.
    for message in body.messages:
        content = _message_text(message)
        if not content:
            continue
        persist_message(message.id, body.thread_id, message.role, content)

    return StreamingResponse(
        run_agent(body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _message_text(message: Any) -> str:
    """Best-effort plain-text extraction from an AG-UI message object."""
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return ""


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------


@app.get("/threads")
def list_recent_threads(limit: int = 50):
    """List recently active threads (for a "recent chats" screen)."""
    return {"threads": list_threads(limit=limit)}


@app.get("/threads/{thread_id}/messages")
def thread_history(thread_id: str):
    """Return the full persisted message history for a thread, so a
    client can restore a conversation (e.g. after reopening the app)."""
    return {"thread_id": thread_id, "messages": get_thread_messages(thread_id)}


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
    image_path: str | None = None  # local server path, e.g. from POST /upload
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
    for message in body.messages:
        content = _message_text(message)
        if content:
            persist_message(message.id, thread_id, message.role, content)

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


app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount(
    "/", StaticFiles(directory=str(BASE_DIR / "static"), html=True), name="static"
)
