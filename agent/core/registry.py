"""
Registry for assembling the tools available to the orchestrator and its
subagents — native tool groups plus whatever MCP servers are self-discovered
from .env.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool

from ..mcp import discover_mcp_tools
from ..tools import (
    CALENDAR_TOOLS,
    COMMERCE_TOOLS,
    COMMUNICATION_TOOLS,
    PET_PROFILE_TOOLS,
    SEARCH_TOOLS,
)

# Native tool groups, keyed by the group name subagent AGENT.md files
# reference in their `tools:` frontmatter field.
_NATIVE_TOOL_GROUPS: dict[str, list[BaseTool]] = {
    "communication": COMMUNICATION_TOOLS,
    "commerce": COMMERCE_TOOLS,
    "calendar": CALENDAR_TOOLS,
    "pet_profile": PET_PROFILE_TOOLS,
    "search": SEARCH_TOOLS,
}


async def build_tool_groups(
    extra_tools: list[BaseTool] | None = None,
) -> dict[str, list[BaseTool]]:
    """
    Build the full name -> tool-list mapping used both for the orchestrator's
    flat tool list and for assigning tool groups to subagents.

    MCP server names (e.g. 'maps', 'wikipedia', or anything else added to
    MCP_SERVERS in .env) become tool-group keys automatically — no code
    change needed here when a new plugin is added.
    """
    groups: dict[str, list[BaseTool]] = dict(_NATIVE_TOOL_GROUPS)

    mcp_tools_by_server = await discover_mcp_tools()
    groups.update(mcp_tools_by_server)

    if extra_tools:
        groups["extra"] = extra_tools

    return groups


async def build_tools(extra_tools: list[BaseTool] | None = None) -> list[BaseTool]:
    """Flat list of every tool (native + MCP-discovered) for the orchestrator."""
    groups = await build_tool_groups(extra_tools)
    return [tool for tools in groups.values() for tool in tools]
