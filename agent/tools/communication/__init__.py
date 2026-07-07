"""Outbound communication tools (call / email / WhatsApp) — all stubbed."""

from .call_tool import COMMUNICATION_CALL_TOOLS
from .email_tool import COMMUNICATION_EMAIL_TOOLS
from .whatsapp_tool import COMMUNICATION_WHATSAPP_TOOLS

COMMUNICATION_TOOLS = [
    *COMMUNICATION_CALL_TOOLS,
    *COMMUNICATION_EMAIL_TOOLS,
    *COMMUNICATION_WHATSAPP_TOOLS,
]

__all__ = ["COMMUNICATION_TOOLS"]
