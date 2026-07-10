"""Outbound WhatsApp communication tool (Green API) — stubbed until configured."""

from .whatsapp_tool import COMMUNICATION_WHATSAPP_TOOLS

COMMUNICATION_TOOLS = [
    *COMMUNICATION_WHATSAPP_TOOLS,
]

__all__ = ["COMMUNICATION_TOOLS"]
