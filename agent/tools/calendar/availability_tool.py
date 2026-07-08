"""
User calendar availability tool — Google Calendar integration.

Set these in .env to activate real calendar lookups:

    CALENDAR_PROVIDER=google
    GOOGLE_CALENDAR_CREDENTIALS_JSON=<service-account-key-as-minified-json>
    GOOGLE_CALENDAR_ID=<calendar-id>   # optional, defaults to "primary"

With CALENDAR_PROVIDER=stub (or unset), the tool returns illustrative
placeholder slots so the rest of the booking workflow can be developed
and tested without real credentials.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BUSINESS_HOUR_START = 8   # 8 AM
BUSINESS_HOUR_END = 20    # 8 PM
MIN_SLOT_MINUTES = 30     # shortest appointment we'll propose
MAX_RANGE_DAYS = 7        # cap the query window to avoid huge responses

TIMEDELTA_MIN_SLOT = timedelta(minutes=MIN_SLOT_MINUTES)


# ---------------------------------------------------------------------------
# Public tool — signature preserved from the stub for full backwards compat
# ---------------------------------------------------------------------------

@tool
def get_user_availability(
    earliest: str,
    latest: str,
) -> dict[str, Any]:
    """
    Get the user's free time slots within a date range, to propose as
    candidate appointment times to a vet clinic.

    Args:
        earliest: ISO date/time to start searching from (e.g. '2026-07-08').
        latest: ISO date/time to search until (e.g. '2026-07-10').

    Returns:
        A dict with:
          - source: "google_calendar" | "stubbed" | "error"
          - earliest / latest: the request parameters echoed back
          - free_slots: list of {"start": "<iso>", "end": "<iso>"}
          - note: human-readable status message
    """
    provider = os.getenv("CALENDAR_PROVIDER", "stub")

    if provider == "google":
        return _check_google_calendar(earliest, latest)

    # -- stub fallback (unchanged from original) --------------------------
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
            "Calendar provider not configured. Set CALENDAR_PROVIDER=google, "
            "GOOGLE_CALENDAR_CREDENTIALS_JSON, and (optionally) "
            "GOOGLE_CALENDAR_ID in .env."
        ),
    }


# ---------------------------------------------------------------------------
# Google Calendar implementation
# ---------------------------------------------------------------------------

def _check_google_calendar(earliest: str, latest: str) -> dict[str, Any]:
    creds_json = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_JSON")
    if not creds_json:
        return _error_result(earliest, latest,
                             "GOOGLE_CALENDAR_CREDENTIALS_JSON not set in .env")

    try:
        service = _build_service(creds_json)
    except Exception as exc:
        return _error_result(earliest, latest,
                             f"Failed to build Calendar service: {exc}")

    try:
        start_dt = _parse_dt(earliest)
        end_dt = _parse_dt(latest)
    except ValueError as exc:
        return _error_result(earliest, latest, f"Invalid date: {exc}")

    if end_dt - start_dt > timedelta(days=MAX_RANGE_DAYS):
        end_dt = start_dt + timedelta(days=MAX_RANGE_DAYS)

    calendar_id = os.getenv("GOOGLE_CALENDAR_ID") or "primary"

    try:
        busy = _fetch_busy_periods(service, calendar_id, start_dt, end_dt)
    except Exception as exc:
        return _error_result(earliest, latest,
                             f"Google Calendar API error: {exc}")

    free_slots = _compute_free_slots(start_dt, end_dt, busy)

    return {
        "source": "google_calendar",
        "earliest": earliest,
        "latest": latest,
        "free_slots": free_slots,
        "note": f"Using Google Calendar ({calendar_id})",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_service(creds_json: str) -> Any:
    """Authenticate with a service-account JSON key and return the Calendar
    v3 service resource."""
    from google.auth import load_credentials_from_dict
    from googleapiclient.discovery import build

    creds = load_credentials_from_dict(json.loads(creds_json))[0]
    return build("calendar", "v3", credentials=creds)


def _fetch_busy_periods(
    service: Any,
    calendar_id: str,
    start_dt: datetime,
    end_dt: datetime,
) -> list[tuple[datetime, datetime]]:
    """Return a sorted, non-overlapping list of (start, end) busy periods."""
    body = {
        "timeMin": start_dt.isoformat(),
        "timeMax": end_dt.isoformat(),
        "items": [{"id": calendar_id}],
    }
    raw = service.freebusy().query(body=body).execute()
    busy_raw = (
        raw.get("calendars", {})
        .get(calendar_id, {})
        .get("busy", [])
    )

    periods: list[tuple[datetime, datetime]] = []
    for b in busy_raw:
        periods.append((_parse_dt(b["start"]), _parse_dt(b["end"])))

    periods.sort(key=lambda x: x[0])

    # merge overlapping / adjacent periods
    merged: list[tuple[datetime, datetime]] = []
    for start, end in periods:
        if merged and start <= merged[-1][1]:
            # extend the last period
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
    """Within *window_start..window_end* and business hours, return every
    contiguous block of free time ≥ MIN_SLOT_MINUTES as
    ``{"start": "<iso>", "end": "<iso>"}``."""
    slots: list[dict[str, str]] = []
    cursor = window_start
    busy_idx = 0

    while cursor < window_end:
        # snap to business hours for the current day
        day_start = cursor.replace(hour=BUSINESS_HOUR_START, minute=0,
                                   second=0, microsecond=0)
        day_end = cursor.replace(hour=BUSINESS_HOUR_END, minute=0,
                                 second=0, microsecond=0)

        if cursor < day_start:
            cursor = day_start

        if cursor >= day_end:
            # move to next day, 00:00
            cursor = (cursor + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0)
            continue

        # skip busy periods that end before our cursor
        while busy_idx < len(busy) and busy[busy_idx][1] <= cursor:
            busy_idx += 1

        # determine how far the current free block extends
        if busy_idx < len(busy) and busy[busy_idx][0] < day_end:
            busy_start = max(busy[busy_idx][0], cursor)
            block_end = min(busy_start, day_end)
        else:
            block_end = day_end

        if block_end - cursor >= TIMEDELTA_MIN_SLOT:
            slots.append({
                "start": cursor.isoformat(),
                "end": block_end.isoformat(),
            })

        # advance cursor past this busy period (or to end of day)
        if busy_idx < len(busy) and busy[busy_idx][0] < day_end:
            cursor = max(cursor, busy[busy_idx][1])
        else:
            cursor = day_end

    return slots


def _parse_dt(value: str) -> datetime:
    """Parse an ISO datetime or date string into an aware UTC datetime."""
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        dt = datetime.fromisoformat(f"{value}T00:00:00")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _error_result(
    earliest: str, latest: str, note: str,
) -> dict[str, Any]:
    return {
        "source": "error",
        "earliest": earliest,
        "latest": latest,
        "free_slots": [],
        "note": note,
    }


CALENDAR_TOOLS = [get_user_availability]
