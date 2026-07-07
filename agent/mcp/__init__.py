"""
Self-discovering MCP integration layer.

Add a new plugin by editing .env only (see .env.example) — no imports or
code changes are needed here. `discover_mcp_tools()` reads MCP_SERVERS at
startup and connects to whatever is listed.
"""

from .config import MCPServerSpec, build_server_specs
from .loader import discover_mcp_tools, get_all_mcp_tools, get_mcp_tools_for

__all__ = [
    "MCPServerSpec",
    "build_server_specs",
    "discover_mcp_tools",
    "get_all_mcp_tools",
    "get_mcp_tools_for",
]
