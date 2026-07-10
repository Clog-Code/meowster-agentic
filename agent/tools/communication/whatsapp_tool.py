"""
WhatsApp messaging tool backed by Green API (green-api.com).

Configure GREEN_API_INSTANCE_ID, GREEN_API_TOKEN and RECIPIENT_NUMBER in
.env (see .env.example). Messages are delivered to `to_number`; if that is
empty, RECIPIENT_NUMBER is used as a fallback. Note: on the free Green API
Developer plan, only the instance owner's verified number can receive
messages, so arbitrary `to_number` values may not be delivered. If Green API
is not configured, the tool returns a mocked confirmation so the agent still
runs end-to-end.
"""

import os
import uuid
from datetime import UTC, datetime
from typing import Any

import requests
from langchain_core.tools import tool

GREEN_API_BASE = "https://api.green-api.com"


def _green_api_configured() -> bool:
    return bool(
        os.getenv("GREEN_API_INSTANCE_ID")
        and os.getenv("GREEN_API_TOKEN")
        and os.getenv("RECIPIENT_NUMBER")
    )


def _stub(to_number: str, message: str) -> dict[str, Any]:
    return {
        "message_id": f"stub-{uuid.uuid4().hex[:8]}",
        "status": "stubbed",
        "to_number": to_number,
        "message_preview": message[:200],
        "timestamp": datetime.now(UTC).isoformat(),
        "note": (
            "Green API not configured. Set GREEN_API_INSTANCE_ID, "
            "GREEN_API_TOKEN and RECIPIENT_NUMBER in .env to send real "
            "WhatsApp messages."
        ),
    }


@tool
def send_whatsapp_message(
    to_number: str,
    message: str,
) -> dict[str, Any]:
    """
    Send a WhatsApp message, e.g. an appointment request or an order
    confirmation to a shop/clinic that lists WhatsApp as a contact channel.

    Uses Green API (green-api.com). On the free Developer plan the message is
    delivered to RECIPIENT_NUMBER (your number). `to_number` is recorded for
    reference only. If Green API is not configured, the tool returns a stubbed
    confirmation instead of failing.

    Args:
        to_number: Recipient's phone number in international format, e.g. '+60123456789'.
        message: Message body text.

    Returns:
        A send record. `status` is 'sent', 'error' or 'stubbed'.
    """
    if not _green_api_configured():
        return _stub(to_number, message)

    instance_id = os.getenv("GREEN_API_INSTANCE_ID")
    token = os.getenv("GREEN_API_TOKEN")
    recipient = os.getenv("RECIPIENT_NUMBER")
    assert instance_id and token and recipient

    chat_id = f"{recipient.lstrip('+')}@c.us"
    url = f"{GREEN_API_BASE}/waInstance{instance_id}/sendMessage/{token}"
    payload = {"chatId": chat_id, "message": message}

    try:
        resp = requests.post(url, json=payload, timeout=10)
    except requests.RequestException as exc:
        return {
            "message_id": None,
            "status": "error",
            "to_number": to_number,
            "recipient": recipient,
            "error": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    data = resp.json()
    if data.get("error"):
        return {
            "message_id": None,
            "status": "error",
            "to_number": to_number,
            "recipient": recipient,
            "error": data.get("message") or data.get("errMsg"),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    resp.raise_for_status()
    return {
        "message_id": data.get("idMessage"),
        "status": "sent",
        "to_number": to_number,
        "recipient": recipient,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@tool
def check_whatsapp_number(
    phone_number: str,
) -> dict[str, Any]:
    """
    Check whether a phone number is registered on WhatsApp before attempting
    to message it. Always call this first when you have a clinic/shop number
    from Maps and want to confirm it is reachable via WhatsApp.

    Uses Green API (green-api.com). Requires GREEN_API_INSTANCE_ID,
    GREEN_API_TOKEN and RECIPIENT_NUMBER in .env. If Green API is not
    configured, returns a stubbed 'unknown' result.

    Args:
        phone_number: Phone number in international format, e.g. '+60123456789'
            or '60123456789'. Country code required, no spaces or dashes.

    Returns:
        A record with `is_on_whatsapp` (bool) and `status` ('ok' | 'error' | 'stubbed').
    """
    if not _green_api_configured():
        return {
            "phone_number": phone_number,
            "is_on_whatsapp": False,
            "status": "stubbed",
            "note": "Green API not configured; cannot verify WhatsApp registration.",
        }

    instance_id = os.getenv("GREEN_API_INSTANCE_ID")
    token = os.getenv("GREEN_API_TOKEN")
    assert instance_id and token

    url = f"{GREEN_API_BASE}/waInstance{instance_id}/checkWhatsapp/{token}"
    payload = {"phoneNumber": phone_number.lstrip("+")}

    try:
        resp = requests.post(url, json=payload, timeout=10)
    except requests.RequestException as exc:
        return {
            "phone_number": phone_number,
            "is_on_whatsapp": False,
            "status": "error",
            "error": str(exc),
        }

    data = resp.json()
    if data.get("error"):
        return {
            "phone_number": phone_number,
            "is_on_whatsapp": False,
            "status": "error",
            "error": data.get("message") or data.get("errMsg"),
        }

    resp.raise_for_status()
    return {
        "phone_number": phone_number,
        "is_on_whatsapp": bool(data.get("existsWhatsapp")),
        "status": "ok",
    }


COMMUNICATION_WHATSAPP_TOOLS = [send_whatsapp_message, check_whatsapp_number]
