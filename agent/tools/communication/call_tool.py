"""
Outbound phone call tool — STUB.

TODO(you): wire this up to a real voice provider, e.g. Twilio Programmable
Voice (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER in .env)
or a click-to-call / IVR API from the clinic's side.

Until then, `make_phone_call` just logs the intended call and returns a
mocked confirmation so the rest of the agent (subagent prompts, AG-UI
events, downstream summary logic) can be built and tested end-to-end.
"""

import os
import uuid
from datetime import UTC, datetime
from typing import Any

from langchain_core.tools import tool


@tool
def make_phone_call(
    to_number: str,
    purpose: str,
    talking_points: list[str],
) -> dict[str, Any]:
    """
    Place an outbound phone call, e.g. to a vet clinic to request or confirm
    an appointment.

    Args:
        to_number: E.164 phone number to call (e.g. '+60123456789').
        purpose: Short label for why the call is being made
            (e.g. 'book_emergency_appointment').
        talking_points: Ordered list of things the call should communicate
            or ask (e.g. pet symptoms, requested time slots).

    Returns:
        A call record. Until a real provider is wired in (see TODO in
        call_tool.py), `status` will always be 'stubbed' and no call is
        actually placed.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")

    if not (account_sid and auth_token and from_number):
        return {
            "call_id": f"stub-{uuid.uuid4().hex[:8]}",
            "status": "stubbed",
            "to_number": to_number,
            "purpose": purpose,
            "talking_points": talking_points,
            "timestamp": datetime.now(UTC).isoformat(),
            "note": (
                "Voice provider not configured. Set TWILIO_ACCOUNT_SID, "
                "TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER in .env, then "
                "implement the real call in call_tool.py."
            ),
        }

    # ------------------------------------------------------------------
    # TODO(you): real implementation, e.g.:
    #
    #   from twilio.rest import Client
    #   client = Client(account_sid, auth_token)
    #   call = client.calls.create(
    #       to=to_number,
    #       from_=from_number,
    #       twiml=f"<Response><Say>{'. '.join(talking_points)}</Say></Response>",
    #   )
    #   return {"call_id": call.sid, "status": call.status, ...}
    # ------------------------------------------------------------------
    raise NotImplementedError("Real voice-call integration not yet implemented.")


COMMUNICATION_CALL_TOOLS = [make_phone_call]
