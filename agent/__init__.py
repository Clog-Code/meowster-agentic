"""
Native (non-MCP) tool exports for the agent runtime.

MCP-discovered tools (maps, wikipedia, and anything else added via .env) are
NOT listed here — they're loaded dynamically at runtime by
`agent.mcp.discover_mcp_tools()` and merged in by `core/registry.py`.
"""

from .tools.calendar import CALENDAR_TOOLS
from .tools.commerce import COMMERCE_TOOLS
from .tools.communication import COMMUNICATION_TOOLS
from .tools.pet_profile import PET_PROFILE_TOOLS

__all__ = [  # pylint: disable=duplicate-code
    "CALENDAR_TOOLS",
    "COMMERCE_TOOLS",
    "COMMUNICATION_TOOLS",
    "PET_PROFILE_TOOLS",
]
