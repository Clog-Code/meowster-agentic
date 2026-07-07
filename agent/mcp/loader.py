"""
Runtime MCP tool discovery.

`load_mcp_tools_by_server()` connects to every server described in .env
(see agent/mcp/config.py) and asks each one for its full tool list via the
Model Context Protocol — nothing about individual tools (names, schemas,
descriptions) is hardcoded anywhere in this codebase. Whatever the plugin
exposes is what the agent gets.

Requires: `pip install langchain-mcp-adapters`
"""

from __future__ import annotations

import logging

from langchain_core.tools import BaseTool

from .config import build_server_specs

logger = logging.getLogger(__name__)

# Populated lazily on first successful discovery; keyed by server name.
_TOOLS_BY_SERVER: dict[str, list[BaseTool]] = {}
_DISCOVERED = False


async def discover_mcp_tools(force: bool = False) -> dict[str, list[BaseTool]]:
    """
    Connect to every MCP server declared in MCP_SERVERS and return the tools
    each one exposes, keyed by server name.

    Safe to call multiple times — results are cached after the first
    successful discovery unless `force=True`.
    """
    global _DISCOVERED

    if _DISCOVERED and not force:
        return _TOOLS_BY_SERVER

    specs = build_server_specs()
    if not specs:
        logger.warning(
            "No MCP servers configured (MCP_SERVERS is empty or all entries "
            "were skipped). The agent will run with native tools only."
        )
        _DISCOVERED = True
        return _TOOLS_BY_SERVER

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError as exc:
        raise RuntimeError(
            "langchain-mcp-adapters is not installed. Run: "
            "pip install langchain-mcp-adapters"
        ) from exc

    connections = {spec.name: spec.to_langchain_mcp_connection() for spec in specs}
    client = MultiServerMCPClient(connections)

    for spec in specs:
        try:
            server_tools = await client.get_tools(server_name=spec.name)
            _TOOLS_BY_SERVER[spec.name] = server_tools
            logger.info(
                "Discovered %d tool(s) from MCP server '%s': %s",
                len(server_tools),
                spec.name,
                ", ".join(t.name for t in server_tools) or "(none)",
            )
        except Exception:
            logger.exception("Failed to load tools from MCP server '%s' — skipping.", spec.name)
            _TOOLS_BY_SERVER[spec.name] = []

    _DISCOVERED = True
    return _TOOLS_BY_SERVER


async def get_all_mcp_tools() -> list[BaseTool]:
    """Flat list of every tool discovered across all configured MCP servers."""
    by_server = await discover_mcp_tools()
    return [tool for tools in by_server.values() for tool in tools]


async def get_mcp_tools_for(server_name: str) -> list[BaseTool]:
    """Tools for one specific server, e.g. get_mcp_tools_for('maps')."""
    by_server = await discover_mcp_tools()
    return by_server.get(server_name.lower(), [])
