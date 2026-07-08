"""Unit tests for MCP server self-discovery from environment variables."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# pylint: disable-next=wrong-import-position
from agent.mcp.config import build_server_specs


def _clear_mcp_env():
    for key in list(os.environ):
        if key.startswith("MCP_"):
            del os.environ[key]


def test_discovers_http_server_from_env():
    """Discover an HTTP-based MCP server from env vars."""
    _clear_mcp_env()
    os.environ["MCP_SERVERS"] = "maps"
    os.environ["MCP_MAPS_URL"] = "https://example.com/mcp"
    os.environ["MCP_MAPS_TRANSPORT"] = "streamable_http"
    os.environ["MCP_MAPS_API_KEY"] = "secret123"

    specs = build_server_specs()
    assert len(specs) == 1
    assert specs[0].name == "maps"
    assert specs[0].url == "https://example.com/mcp"
    conn = specs[0].to_langchain_mcp_connection()
    assert conn["headers"]["Authorization"] == "Bearer secret123"


def test_skips_server_missing_url():
    """Skip a server entry when its URL env var is not set."""
    _clear_mcp_env()
    os.environ["MCP_SERVERS"] = "wikipedia"
    # MCP_WIKIPEDIA_URL intentionally not set

    specs = build_server_specs()
    assert not specs


def test_adding_new_plugin_requires_no_code_change():
    """Simulates adding a third plugin purely via env vars."""
    _clear_mcp_env()
    os.environ["MCP_SERVERS"] = "maps,wikipedia,petstore"
    os.environ["MCP_MAPS_URL"] = "https://maps.example.com/mcp"
    os.environ["MCP_WIKIPEDIA_URL"] = "https://wiki.example.com/mcp"
    os.environ["MCP_PETSTORE_URL"] = "https://petstore.example.com/mcp"

    specs = build_server_specs()
    names = {s.name for s in specs}
    assert names == {"maps", "wikipedia", "petstore"}


def test_stdio_transport():
    """Configure a stdio-based MCP server via env vars."""
    _clear_mcp_env()
    os.environ["MCP_SERVERS"] = "local"
    os.environ["MCP_LOCAL_TRANSPORT"] = "stdio"
    os.environ["MCP_LOCAL_COMMAND"] = "npx some-mcp-server"

    specs = build_server_specs()
    assert len(specs) == 1
    conn = specs[0].to_langchain_mcp_connection()
    assert conn["transport"] == "stdio"
    assert conn["command"] == "npx"
    assert conn["args"] == ["some-mcp-server"]


def test_stdio_transport_with_env():
    """Configure a stdio MCP server with API key passthrough."""
    _clear_mcp_env()
    os.environ["MCP_SERVERS"] = "maps"
    os.environ["MCP_MAPS_TRANSPORT"] = "stdio"
    os.environ["MCP_MAPS_COMMAND"] = "npx @modelcontextprotocol/server-google-maps"
    os.environ["MCP_MAPS_API_KEY"] = "test-key-123"

    specs = build_server_specs()
    assert specs[0].name == "maps"
    assert specs[0].command == "npx"
    assert specs[0].args == ["@modelcontextprotocol/server-google-maps"]
    assert specs[0].env == {"GOOGLE_MAPS_API_KEY": "test-key-123"}
    conn = specs[0].to_langchain_mcp_connection()
    assert conn["transport"] == "stdio"
    assert conn["command"] == "npx"
    assert conn["args"] == ["@modelcontextprotocol/server-google-maps"]
    assert conn["env"] == {"GOOGLE_MAPS_API_KEY": "test-key-123"}
