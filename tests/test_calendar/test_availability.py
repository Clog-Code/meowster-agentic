"""Unit tests for the calendar availability tool (no network needed)."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

# pylint: disable=wrong-import-position
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agent.tools.calendar.availability_tool import (
    _compute_free_slots,
    _parse_dt,
    get_user_availability,
    list_calendar_events,
)

# ---------------------------------------------------------------------------
# _parse_dt
# ---------------------------------------------------------------------------


def test_parse_dt_parses_iso_datetime():
    """Parses a full ISO datetime string with timezone."""
    dt = _parse_dt("2026-07-08T14:30:00+00:00")
    assert dt == datetime(2026, 7, 8, 14, 30, tzinfo=UTC)


def test_parse_dt_parses_date_only():
    """Parses a date-only string, defaulting to midnight UTC."""
    dt = _parse_dt("2026-07-08")
    assert dt == datetime(2026, 7, 8, tzinfo=UTC)


def test_parse_dt_naive_datetime_gets_utc():
    """Attaches UTC to naive datetime strings."""
    dt = _parse_dt("2026-07-08T10:00:00")
    assert dt.tzinfo is UTC


def test_parse_dt_handles_z_suffix():
    """Handles ISO datetime with Z suffix."""
    dt = _parse_dt("2026-07-08T10:00:00Z")
    assert dt == datetime(2026, 7, 8, 10, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# _compute_free_slots
# ---------------------------------------------------------------------------

BUSINESS_START = 8
BUSINESS_END = 20


def _slot(
    start_hour: int, end_hour: int, day: str = "2026-07-08"
) -> tuple[datetime, datetime]:
    return (
        datetime.fromisoformat(f"{day}T{start_hour:02d}:00:00+00:00"),
        datetime.fromisoformat(f"{day}T{end_hour:02d}:00:00+00:00"),
    )


def test_compute_free_slots_no_busy_periods():
    """Returns the full business day when there are no busy periods."""
    start = datetime(2026, 7, 8, 0, 0, tzinfo=UTC)
    end = datetime(2026, 7, 8, 23, 59, tzinfo=UTC)
    slots = _compute_free_slots(start, end, [])
    assert len(slots) == 1
    assert slots[0]["start"] == f"2026-07-08T{BUSINESS_START:02d}:00:00+00:00"
    assert slots[0]["end"] == f"2026-07-08T{BUSINESS_END:02d}:00:00+00:00"


def test_compute_free_slots_with_busy_midday():
    """Splits free slots around a midday busy period."""
    start = datetime(2026, 7, 8, 0, 0, tzinfo=UTC)
    end = datetime(2026, 7, 8, 23, 59, tzinfo=UTC)
    busy = [_slot(12, 13)]
    slots = _compute_free_slots(start, end, busy)
    assert len(slots) == 2
    assert slots[0] == {
        "start": "2026-07-08T08:00:00+00:00",
        "end": "2026-07-08T12:00:00+00:00",
    }
    assert slots[1] == {
        "start": "2026-07-08T13:00:00+00:00",
        "end": "2026-07-08T20:00:00+00:00",
    }


def test_compute_free_slots_merges_overlapping_busy():
    """Merges overlapping busy periods before computing free slots."""
    start = datetime(2026, 7, 8, 0, 0, tzinfo=UTC)
    end = datetime(2026, 7, 8, 23, 59, tzinfo=UTC)
    busy = [_slot(10, 12), _slot(11, 14)]
    slots = _compute_free_slots(start, end, busy)
    assert len(slots) == 2
    assert slots[0]["end"] == "2026-07-08T10:00:00+00:00"
    assert slots[1]["start"] == "2026-07-08T14:00:00+00:00"


def test_compute_free_slots_filters_short_slots():
    """Filters out free slots shorter than MIN_SLOT_MINUTES."""
    start = datetime(2026, 7, 8, 0, 0, tzinfo=UTC)
    end = datetime(2026, 7, 8, 23, 59, tzinfo=UTC)
    busy = [
        (
            datetime(2026, 7, 8, 8, 10, tzinfo=UTC),
            datetime(2026, 7, 8, 19, 50, tzinfo=UTC),
        ),
    ]
    slots = _compute_free_slots(start, end, busy)
    assert len(slots) == 0


def test_compute_free_slots_busy_at_business_start():
    """Handles busy periods that start exactly at business hours."""
    start = datetime(2026, 7, 8, 0, 0, tzinfo=UTC)
    end = datetime(2026, 7, 8, 23, 59, tzinfo=UTC)
    busy = [_slot(8, 13)]
    slots = _compute_free_slots(start, end, busy)
    assert len(slots) == 1
    assert slots[0]["start"] == "2026-07-08T13:00:00+00:00"


def test_compute_free_slots_multiple_days():
    """Correctly computes free slots across multiple days."""
    start = datetime(2026, 7, 8, 0, 0, tzinfo=UTC)
    end = datetime(2026, 7, 9, 23, 59, tzinfo=UTC)
    busy = [_slot(12, 13, "2026-07-08"), _slot(14, 15, "2026-07-09")]
    slots = _compute_free_slots(start, end, busy)
    assert len(slots) == 4


# ---------------------------------------------------------------------------
# Live integration tests — only run when real Google creds are configured
# ---------------------------------------------------------------------------

HAS_GOOGLE_CALENDAR = (
    os.getenv("CALENDAR_PROVIDER") == "google"
    and os.getenv("GOOGLE_CALENDAR_CREDENTIALS_JSON") is not None
)


def test_calendar_tools_exported():
    """Both tools are exported in CALENDAR_TOOLS."""
    # pylint: disable=import-outside-toplevel
    from agent.tools.calendar.availability_tool import CALENDAR_TOOLS

    tool_names = {t.name for t in CALENDAR_TOOLS}
    assert "get_user_availability" in tool_names
    assert "list_calendar_events" in tool_names


def test_calendar_tools_exports_via_package():
    """CALENDAR_TOOLS is re-exported from the package __init__."""
    # pylint: disable=import-outside-toplevel
    from agent.tools.calendar import CALENDAR_TOOLS

    tool_names = {t.name for t in CALENDAR_TOOLS}
    assert "get_user_availability" in tool_names
    assert "list_calendar_events" in tool_names


@pytest.mark.skipif(not HAS_GOOGLE_CALENDAR, reason="Google Calendar not configured")
def test_live_google_calendar():
    """Runs live calendar availability test when Google Calendar is configured."""
    result = get_user_availability.invoke(
        {"earliest": "2026-07-08", "latest": "2026-07-10"}
    )
    assert result["source"] == "google_calendar", result.get("note", "")
    for s in result["free_slots"]:
        assert "start" in s
        assert "end" in s


@pytest.mark.skipif(not HAS_GOOGLE_CALENDAR, reason="Google Calendar not configured")
def test_live_list_calendar_events():
    """Runs live calendar events test when Google Calendar is configured."""
    result = list_calendar_events.invoke(
        {"earliest": "2026-07-08", "latest": "2026-07-10"}
    )
    assert result["source"] == "google_calendar", result.get("note", "")
    assert "events" in result
