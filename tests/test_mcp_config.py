"""Unit tests for MCP server self-discovery from environment variables."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.mcp.config import build_server_specs


def _clear_mcp_env():
    for key in list(os.environ):
        if key.startswith("MCP_"):
            del os.environ[key]


def test_discovers_http_server_from_env():
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
    _clear_mcp_env()
    os.environ["MCP_SERVERS"] = "wikipedia"
    # MCP_WIKIPEDIA_URL intentionally not set

    specs = build_server_specs()
    assert specs == []


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
    _clear_mcp_env()
    os.environ["MCP_SERVERS"] = "local"
    os.environ["MCP_LOCAL_TRANSPORT"] = "stdio"
    os.environ["MCP_LOCAL_COMMAND"] = "npx"
    os.environ["MCP_LOCAL_ARGS"] = "-y some-mcp-server"

    specs = build_server_specs()
    assert len(specs) == 1
    conn = specs[0].to_langchain_mcp_connection()
    assert conn["transport"] == "stdio"
    assert conn["command"] == "npx"
    assert conn["args"] == ["-y", "some-mcp-server"]


if __name__ == "__main__":
    import inspect

    test_functions = [
        obj for name, obj in list(globals().items()) if name.startswith("test_") and inspect.isfunction(obj)
    ]
    failures = 0
    for fn in test_functions:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError:
            failures += 1
            print(f"FAIL  {fn.__name__}")
    print(f"\n{len(test_functions) - failures}/{len(test_functions)} passed")
    sys.exit(1 if failures else 0)
