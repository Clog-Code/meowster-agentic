"""
User calendar availability tool — Google Calendar integration with OAuth.

The tool tries three authentication methods in order:

1. User OAuth token stored in the DB for the current thread_id
   (acquired via the /auth/google OAuth flow in the dashboard).
2. GOOGLE_CALENDAR_CREDENTIALS_JSON service-account key from .env.
3. Stub placeholder slots (CALENDAR_PROVIDER=stub or unset).

Set these in .env for methods 2/3:

    CALENDAR_PROVIDER=google
    GOOGLE_CALENDAR_CREDENTIALS_JSON=<service-account-key-as-minified-json>
    GOOGLE_CALENDAR_ID=you@gmail.com

For method 1 (per-user OAuth), set these in .env:

    GOOGLE_OAUTH_CLIENT_ID=...
    GOOGLE_OAUTH_CLIENT_SECRET=...
    GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/auth/google/callback
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import sqlite3

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from backend.config import DATABASE_PATH

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BUSINESS_HOUR_START = 8
BUSINESS_HOUR_END = 20
MIN_SLOT_MINUTES = 30
MAX_RANGE_DAYS = 7

TIMEDELTA_MIN_SLOT = timedelta(minutes=MIN_SLOT_MINUTES)


# ---------------------------------------------------------------------------
# Public tool
# ---------------------------------------------------------------------------


@tool
def get_user_availability(
    earliest: str,
    latest: str,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    """
    Get the user's free time slots within a date range, to propose as
    candidate appointment times to a vet clinic.

    Authentication priority:
      1. User OAuth token (stored via /auth/google OAuth flow) for the
         current conversation thread.
      2. Service account from GOOGLE_CALENDAR_CREDENTIALS_JSON in .env.
      3. Stubbed placeholder slots (for development).

    Args:
        earliest: ISO date/time to start searching from (e.g. '2026-07-08').
        latest: ISO date/time to search until (e.g. '2026-07-10').

    Returns:
        A dict with:
          - source: "user_oauth" | "google_calendar" | "stubbed" | "error"
          - earliest / latest: the request parameters echoed back
          - free_slots: list of {"start": "<iso>", "end": "<iso>"}
          - note: human-readable status message
    """
    thread_id = _get_thread_id(config)

    # 1. Try user OAuth token from DB (per-user, linked to thread_id)
    if thread_id:
        result = _check_user_oauth(earliest, latest, thread_id)
        if result is not None:
            return result

    # 2. Try service account from .env
    if os.getenv("CALENDAR_PROVIDER") == "google":
        result = _check_service_account(earliest, latest)
        if result is not None:
            return result

    # 3. Stub fallback
    try:
        start = datetime.fromisoformat(earliest)
    except (ValueError, TypeError):
        start = datetime.now(UTC)
    slots = [
        {
            "start": (start + timedelta(hours=h)).isoformat(),
            "end": (start + timedelta(hours=h + 1)).isoformat(),
        }
        for h in (10, 14, 16, 34, 38)
    ]
    return {
        "source": "stubbed",
        "earliest": earliest,
        "latest": latest,
        "free_slots": slots,
        "note": (
            "Calendar provider not configured. Connect your Google Calendar "
            "via the dashboard (/auth/google), or set CALENDAR_PROVIDER=google "
            "and GOOGLE_CALENDAR_CREDENTIALS_JSON in .env."
        ),
    }


# ---------------------------------------------------------------------------
# Auth method 1: per-user OAuth (stored in DB, linked to thread_id)
# ---------------------------------------------------------------------------


def _get_thread_id(config: RunnableConfig | None) -> str | None:
    """Extract thread_id from the agent's runtime config."""
    if config is None:
        return None
    return (config.get("configurable") or {}).get("thread_id")


def _check_user_oauth(
    earliest: str,
    latest: str,
    thread_id: str,
) -> dict[str, Any] | None:
    """Look up a stored user OAuth token and query their calendar.
    Returns None if no token is stored for this thread."""
    token_row = _get_oauth_token(thread_id)
    if token_row is None:
        return None

    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        return _error_result(
            earliest,
            latest,
            "GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET must be set "
            "in .env for user OAuth calendar access.",
        )

    try:
        service = _build_user_service(token_row, client_id, client_secret)
    except Exception as exc:
        return _error_result(
            earliest, latest, f"Failed to build Calendar service from OAuth: {exc}"
        )

    return _query_calendar(service, earliest, latest, "user_oauth")


# ---------------------------------------------------------------------------
# Auth method 2: service account from .env
# ---------------------------------------------------------------------------


def _check_service_account(
    earliest: str,
    latest: str,
) -> dict[str, Any] | None:
    """Use the static service-account key from GOOGLE_CALENDAR_CREDENTIALS_JSON.
    Returns None if the env var is not set."""
    creds_json = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_JSON")
    if not creds_json:
        return None

    try:
        service = _build_service_account_service(creds_json)
    except Exception as exc:
        return _error_result(
            earliest, latest, f"Failed to build Calendar service: {exc}"
        )

    return _query_calendar(service, earliest, latest, "google_calendar")


# ---------------------------------------------------------------------------
# Shared query logic
# ---------------------------------------------------------------------------


def _query_calendar(
    service: Any,
    earliest: str,
    latest: str,
    source: str,
) -> dict[str, Any]:
    """Execute the free/busy query against the given Calendar service."""
    try:
        start_dt = _parse_dt(earliest)
        end_dt = _parse_dt(latest)
    except ValueError as exc:
        return _error_result(earliest, latest, f"Invalid date: {exc}")

    if end_dt - start_dt > timedelta(days=MAX_RANGE_DAYS):
        end_dt = start_dt + timedelta(days=MAX_RANGE_DAYS)

    calendar_id = (
        "primary"
        if source == "user_oauth"
        else os.getenv("GOOGLE_CALENDAR_ID") or "primary"
    )

    try:
        busy = _fetch_busy_periods(service, calendar_id, start_dt, end_dt)
    except Exception as exc:
        return _error_result(earliest, latest, f"Google Calendar API error: {exc}")

    free_slots = _compute_free_slots(start_dt, end_dt, busy)

    note = f"Using Google Calendar ({calendar_id})"
    if calendar_id == "primary" and source != "user_oauth":
        note += (
            " -- 'primary' is the service account's own calendar, not yours. "
            "Set GOOGLE_CALENDAR_ID to your email after sharing your "
            "calendar with the service account."
        )

    return {
        "source": source,
        "earliest": earliest,
        "latest": latest,
        "free_slots": free_slots,
        "note": note,
    }


# ---------------------------------------------------------------------------
# Service builders
# ---------------------------------------------------------------------------


def _build_service_account_service(creds_json: str) -> Any:
    """Build Calendar v3 service from a service-account JSON key."""
    scopes = ["https://www.googleapis.com/auth/calendar.readonly"]
    creds = service_account.Credentials.from_service_account_info(
        json.loads(creds_json), scopes=scopes
    )
    return build("calendar", "v3", credentials=creds)


def _build_user_service(
    token_row: dict[str, Any],
    client_id: str,
    client_secret: str,
) -> Any:
    """Build Calendar v3 service from a stored user OAuth token."""
    creds = Credentials(
        token=token_row["access_token"],
        refresh_token=token_row["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[token_row["scope"]] if token_row.get("scope") else None,
    )
    return build("calendar", "v3", credentials=creds)


# ---------------------------------------------------------------------------
# DB access helpers (avoid circular import with backend.services)
# ---------------------------------------------------------------------------


def _get_oauth_token(thread_id: str) -> dict[str, Any] | None:
    """Read OAuth tokens directly from the SQLite database."""
    try:
        conn = sqlite3.connect(str(DATABASE_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """SELECT provider, thread_id, scope, access_token, refresh_token,
                      token_expiry, user_email
               FROM oauth_tokens
               WHERE provider = 'google' AND thread_id = ?""",
            (thread_id,),
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Calendar API helpers (unchanged)
# ---------------------------------------------------------------------------


def _fetch_busy_periods(
    service: Any,
    calendar_id: str,
    start_dt: datetime,
    end_dt: datetime,
) -> list[tuple[datetime, datetime]]:
    body = {
        "timeMin": start_dt.isoformat(),
        "timeMax": end_dt.isoformat(),
        "items": [{"id": calendar_id}],
    }
    raw = service.freebusy().query(body=body).execute()
    busy_raw = raw.get("calendars", {}).get(calendar_id, {}).get("busy", [])

    periods: list[tuple[datetime, datetime]] = []
    for b in busy_raw:
        periods.append((_parse_dt(b["start"]), _parse_dt(b["end"])))

    periods.sort(key=lambda x: x[0])

    merged: list[tuple[datetime, datetime]] = []
    for start, end in periods:
        if merged and start <= merged[-1][1]:
            prev_start, prev_end = merged.pop()
            merged.append((prev_start, max(prev_end, end)))
        else:
            merged.append((start, end))

    return merged


def _compute_free_slots(
    window_start: datetime,
    window_end: datetime,
    busy: list[tuple[datetime, datetime]],
) -> list[dict[str, str]]:
    slots: list[dict[str, str]] = []
    cursor = window_start
    busy_idx = 0

    while cursor < window_end:
        day_start = cursor.replace(
            hour=BUSINESS_HOUR_START, minute=0, second=0, microsecond=0
        )
        day_end = cursor.replace(
            hour=BUSINESS_HOUR_END, minute=0, second=0, microsecond=0
        )

        cursor = max(cursor, day_start)

        if cursor >= day_end:
            cursor = (cursor + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            continue

        while busy_idx < len(busy) and busy[busy_idx][1] <= cursor:
            busy_idx += 1

        if busy_idx < len(busy) and busy[busy_idx][0] < day_end:
            busy_start = max(busy[busy_idx][0], cursor)
            block_end = min(busy_start, day_end)
        else:
            block_end = day_end

        if block_end - cursor >= TIMEDELTA_MIN_SLOT:
            slots.append(
                {
                    "start": cursor.isoformat(),
                    "end": block_end.isoformat(),
                }
            )

        if busy_idx < len(busy) and busy[busy_idx][0] < day_end:
            cursor = max(cursor, busy[busy_idx][1])
        else:
            cursor = day_end

    return slots


def _parse_dt(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        dt = datetime.fromisoformat(f"{value}T00:00:00")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _error_result(
    earliest: str,
    latest: str,
    note: str,
) -> dict[str, Any]:
    return {
        "source": "error",
        "earliest": earliest,
        "latest": latest,
        "free_slots": [],
        "note": note,
    }


# ---------------------------------------------------------------------------
# Tool 2: list_calendar_events — return actual event details
# ---------------------------------------------------------------------------


@tool
def list_calendar_events(
    earliest: str,
    latest: str,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    """
    List the user's calendar events within a date range, including title,
    start time, and end time.

    Authentication priority:
      1. User OAuth token (stored via /auth/google OAuth flow) for the
         current conversation thread.
      2. Service account from GOOGLE_CALENDAR_CREDENTIALS_JSON in .env.
      3. Stubbed placeholder events (for development).

    Args:
        earliest: ISO date/time to start searching from (e.g. '2026-07-08').
        latest:  ISO date/time to search until (e.g. '2026-07-10').

    Returns:
        A dict with:
          - source: "user_oauth" | "google_calendar" | "stubbed" | "error"
          - earliest / latest: the request parameters echoed back
          - events: list of event dicts with summary, start, end
          - note: human-readable status message
    """
    thread_id = _get_thread_id(config)

    if thread_id:
        result = _check_user_oauth_events(earliest, latest, thread_id)
        if result is not None:
            return result

    if os.getenv("CALENDAR_PROVIDER") == "google":
        result = _check_service_account_events(earliest, latest)
        if result is not None:
            return result

    return _stub_events(earliest, latest)


def _check_user_oauth_events(
    earliest: str,
    latest: str,
    thread_id: str,
) -> dict[str, Any] | None:
    token_row = _get_oauth_token(thread_id)
    if token_row is None:
        return None

    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        return _error_result(
            earliest,
            latest,
            "GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET must be set "
            "in .env for user OAuth calendar access.",
        )

    try:
        service = _build_user_service(token_row, client_id, client_secret)
    except Exception as exc:
        return _error_result(
            earliest, latest, f"Failed to build Calendar service from OAuth: {exc}"
        )

    return _fetch_events(service, earliest, latest, "user_oauth")


def _check_service_account_events(
    earliest: str,
    latest: str,
) -> dict[str, Any] | None:
    creds_json = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_JSON")
    if not creds_json:
        return None

    try:
        service = _build_service_account_service(creds_json)
    except Exception as exc:
        return _error_result(
            earliest, latest, f"Failed to build Calendar service: {exc}"
        )

    return _fetch_events(service, earliest, latest, "google_calendar")


def _fetch_events(
    service: Any,
    earliest: str,
    latest: str,
    source: str,
) -> dict[str, Any]:
    try:
        start_dt = _parse_dt(earliest)
        end_dt = _parse_dt(latest)
    except ValueError as exc:
        return _error_result(earliest, latest, f"Invalid date: {exc}")

    if end_dt - start_dt > timedelta(days=MAX_RANGE_DAYS):
        end_dt = start_dt + timedelta(days=MAX_RANGE_DAYS)

    calendar_id = (
        "primary"
        if source == "user_oauth"
        else os.getenv("GOOGLE_CALENDAR_ID") or "primary"
    )

    try:
        items = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=start_dt.isoformat(),
                timeMax=end_dt.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
            .get("items", [])
        )
        events: list[dict[str, str]] = []
        for item in items:
            start = item.get("start", {})
            end = item.get("end", {})
            events.append(
                {
                    "summary": item.get("summary", "(no title)"),
                    "start": start.get("dateTime") or start.get("date", ""),
                    "end": end.get("dateTime") or end.get("date", ""),
                    "source": "event_details",
                }
            )
    except Exception:
        busy = _fetch_busy_periods(service, calendar_id, start_dt, end_dt)
        events = []
        for start, end in busy:
            events.append(
                {
                    "summary": "Busy",
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "source": "freebusy",
                }
            )

    note = f"Using Google Calendar ({calendar_id})"
    if calendar_id == "primary" and source != "user_oauth":
        note += (
            " -- 'primary' is the service account's own calendar, not yours. "
            "Set GOOGLE_CALENDAR_ID to your email after sharing your "
            "calendar with the service account."
        )

    return {
        "source": source,
        "earliest": earliest,
        "latest": latest,
        "events": events,
        "note": note,
    }


def _stub_events(
    earliest: str,
    latest: str,
) -> dict[str, Any]:
    try:
        start = datetime.fromisoformat(earliest)
    except (ValueError, TypeError):
        start = datetime.now(UTC)
    events = [
        {
            "summary": "Morning check-up",
            "start": (start + timedelta(hours=9)).isoformat(),
            "end": (start + timedelta(hours=10)).isoformat(),
        },
        {
            "summary": "Lunch meeting",
            "start": (start + timedelta(hours=12)).isoformat(),
            "end": (start + timedelta(hours=13)).isoformat(),
        },
    ]
    return {
        "source": "stubbed",
        "earliest": earliest,
        "latest": latest,
        "events": events,
        "note": (
            "Calendar provider not configured. Connect your Google Calendar "
            "via the dashboard (/auth/google), or set CALENDAR_PROVIDER=google "
            "and GOOGLE_CALENDAR_CREDENTIALS_JSON in .env."
        ),
    }


CALENDAR_TOOLS = [get_user_availability, list_calendar_events]
