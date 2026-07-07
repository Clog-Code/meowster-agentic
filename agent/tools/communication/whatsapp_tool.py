"""
WhatsApp messaging tool — STUB.

TODO(you): wire this up to the WhatsApp Business Cloud API
(WHATSAPP_BUSINESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID in .env), or a BSP
such as Twilio's WhatsApp API / 360dialog.

Until then, `send_whatsapp_message` logs the intended message and returns
a mocked confirmation.
"""

import os
import uuid
from datetime import UTC, datetime
from typing import Any

from langchain_core.tools import tool


@tool
def send_whatsapp_message(
    to_number: str,
    message: str,
) -> dict[str, Any]:
    """
    Send a WhatsApp message, e.g. an appointment request or an order
    confirmation to a shop/clinic that lists WhatsApp as a contact channel.

    Args:
        to_number: E.164 phone number (e.g. '+60123456789').
        message: Message body text.

    Returns:
        A send record. Until a real provider is wired in (see TODO in
        whatsapp_tool.py), `status` will always be 'stubbed' and no message
        is actually sent.
    """
    token = os.getenv("WHATSAPP_BUSINESS_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    if not (token and phone_number_id):
        return {
            "message_id": f"stub-{uuid.uuid4().hex[:8]}",
            "status": "stubbed",
            "to_number": to_number,
            "message_preview": message[:200],
            "timestamp": datetime.now(UTC).isoformat(),
            "note": (
                "WhatsApp Business API not configured. Set "
                "WHATSAPP_BUSINESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in "
                ".env, then implement the real send in whatsapp_tool.py."
            ),
        }

    # ------------------------------------------------------------------
    # TODO(you): real implementation, e.g.:
    #
    #   import requests
    #   url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
    #   headers = {"Authorization": f"Bearer {token}"}
    #   payload = {
    #       "messaging_product": "whatsapp",
    #       "to": to_number,
    #       "type": "text",
    #       "text": {"body": message},
    #   }
    #   resp = requests.post(url, headers=headers, json=payload, timeout=10)
    #   resp.raise_for_status()
    #   return {"message_id": resp.json()["messages"][0]["id"], "status": "sent"}
    # ------------------------------------------------------------------
    raise NotImplementedError("Real WhatsApp integration not yet implemented.")


COMMUNICATION_WHATSAPP_TOOLS = [send_whatsapp_message]
