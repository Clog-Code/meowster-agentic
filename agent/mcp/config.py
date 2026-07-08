"""
Builds MCP server connection configs purely from environment variables.

Adding a new MCP plugin means editing .env only:

    MCP_SERVERS=maps,wikipedia,petstore
    MCP_PETSTORE_URL=https://example.com/mcp
    MCP_PETSTORE_TRANSPORT=streamable_http
    MCP_PETSTORE_API_KEY=...

No code in this file, the loader, or the tool registry needs to change —
`build_mcp_connections()` reads whatever names are listed in MCP_SERVERS and
constructs a connection entry for each one at runtime.
"""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass, field
from typing import Any, Literal

from ..config import get_mcp_server_names

Transport = Literal["streamable_http", "sse", "stdio"]

# Maps MCP server short-names to the env var their subprocess expects.
# When MCP_<NAME>_API_KEY is set and transport is stdio, the key is
# passed to the child process under this variable name.
_STDIO_API_KEY_ENV: dict[str, str] = {
    "maps": "GOOGLE_MAPS_API_KEY",
}


@dataclass
class MCPServerSpec:
    """Normalized description of one self-discovered MCP server."""

    name: str
    transport: Transport
    url: str | None = None
    command: str | None = None
    args: list[str] = field(default_factory=list)
    api_key: str | None = None
    env: dict[str, str] | None = None

    def to_langchain_mcp_connection(self) -> dict[str, Any]:
        """
        Convert to the connection dict shape expected by
        `langchain_mcp_adapters.client.MultiServerMCPClient`.
        """
        if self.transport == "stdio":
            result: dict[str, Any] = {
                "transport": "stdio",
                "command": self.command,
                "args": self.args,
            }
            if self.env:
                result["env"] = self.env
            return result

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return {
            "transport": self.transport,
            "url": self.url,
            "headers": headers or None,
        }


def _env(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value else None


def build_server_specs() -> list[MCPServerSpec]:
    """
    Discover every MCP server declared in MCP_SERVERS and build its spec
    from the matching MCP_<NAME>_* environment variables.

    Servers with missing required fields are skipped with a clear reason,
    rather than raising, so one bad entry doesn't take down every plugin.
    """
    specs: list[MCPServerSpec] = []

    for name in get_mcp_server_names():
        upper = name.upper()
        transport = (_env(f"MCP_{upper}_TRANSPORT") or "streamable_http").lower()
        api_key = _env(f"MCP_{upper}_API_KEY")

        if transport == "stdio":
            raw_command = _env(f"MCP_{upper}_COMMAND")
            if not raw_command:
                print(
                    f"[mcp] skipping '{name}': stdio transport requires MCP_{upper}_COMMAND"
                )
                continue
            command_parts = shlex.split(raw_command)
            env = None
            if api_key and name in _STDIO_API_KEY_ENV:
                env = {_STDIO_API_KEY_ENV[name]: api_key}
            specs.append(
                MCPServerSpec(
                    name=name,
                    transport="stdio",
                    command=command_parts[0],
                    args=command_parts[1:],
                    env=env,
                )
            )
            continue

        url = _env(f"MCP_{upper}_URL")
        if not url:
            print(f"[mcp] skipping '{name}': missing MCP_{upper}_URL")
            continue

        if transport not in ("streamable_http", "sse"):
            print(
                f"[mcp] skipping '{name}': unknown transport '{transport}' "
                "(expected streamable_http, sse, or stdio)"
            )
            continue

        specs.append(
            MCPServerSpec(
                name=name,
                transport=transport,  # type: ignore[arg-type]
                url=url,
                api_key=api_key,
            )
        )

    return specs
