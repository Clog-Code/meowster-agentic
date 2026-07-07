"""
User calendar availability tool — STUB.

TODO(you): wire this up to a real calendar provider, e.g. Google Calendar
(GOOGLE_CALENDAR_CREDENTIALS_JSON in .env) or Outlook/Microsoft Graph, so
the agent can check real free/busy slots before proposing an appointment
time to a clinic.

Until then, `get_user_availability` returns a mocked set of open slots for
the next few days so the booking workflow can be built and tested
end-to-end.
"""

import os
from datetime import UTC, datetime, timedelta
from typing import Any

from langchain_core.tools import tool


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
        A dict with a list of free slots. Until a real calendar provider is
        wired in (see TODO in availability_tool.py), `source` will always be
        'stubbed' and the slots are illustrative placeholders, not the
        user's actual calendar.
    """
    provider = os.getenv("CALENDAR_PROVIDER", "stub")

    if provider == "stub":
        try:
            start = datetime.fromisoformat(earliest)
        except ValueError:
            start = datetime.now(UTC)
        slots = [
            {
                "start": (start + timedelta(hours=h)).isoformat(),
                "end": (start + timedelta(hours=h + 1)).isoformat(),
            }
            for h in (10, 14, 16, 34, 38)  # a couple of slots across two days
        ]
        return {
            "source": "stubbed",
            "earliest": earliest,
            "latest": latest,
            "free_slots": slots,
            "note": (
                "Calendar provider not configured. Set CALENDAR_PROVIDER "
                "and provider credentials in .env (e.g. "
                "GOOGLE_CALENDAR_CREDENTIALS_JSON), then implement the real "
                "free/busy lookup in availability_tool.py."
            ),
        }

    # ------------------------------------------------------------------
    # TODO(you): real implementation, e.g. Google Calendar freebusy.query
    # using GOOGLE_CALENDAR_CREDENTIALS_JSON, filtered to `earliest`..`latest`.
    # ------------------------------------------------------------------
    raise NotImplementedError(f"Calendar provider '{provider}' not yet implemented.")


CALENDAR_TOOLS = [get_user_availability]
