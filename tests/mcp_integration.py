"""Integration tests for MCP servers via stdio transport."""

import os
import json
import subprocess
import time
from dotenv import load_dotenv

load_dotenv()


def _send(handle, request_id, method, params=None):
    """Send a JSON-RPC message over stdin."""
    if params is None:
        params = {}
    msg = (
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
        )
        + "\n"
    )
    handle.stdin.write(msg.encode())
    handle.stdin.flush()


def _print_output(proc):
    """Read and print decoded output lines from stdout."""
    proc.stdin.close()
    output = proc.stdout.read().decode()
    for line in output.strip().split("\n"):
        try:
            print(json.dumps(json.loads(line), indent=2))
        except Exception:
            print(line)


def run_google_maps_mcp() -> None:
    """Run the Google Maps MCP test sequence."""
    with subprocess.Popen(
        ["node", "node_modules/@modelcontextprotocol/server-google-maps/dist/index.js"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        assert proc.stdin is not None
        assert proc.stdout is not None

        _send(
            proc,
            1,
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        )

        _send(
            proc,
            2,
            "tools/call",
            {
                "name": "maps_search_places",
                "arguments": {
                    "query": "vet clinic",
                    "location": {"lat": 3.1390, "lng": 101.6869},
                    "radius": 5000,
                },
            },
        )

        _send(
            proc,
            3,
            "tools/call",
            {
                "name": "maps_place_details",
                "arguments": {"place_id": "ChIJp92YC5RLzDER8Augxs2PEn4"},
            },
        )

        time.sleep(3)
        _print_output(proc)


def run_wikipedia_mcp() -> None:
    """Run the Wikipedia MCP test sequence."""
    with subprocess.Popen(
        [os.environ["WIKIPEDIA_MCP_PATH"]],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        assert proc.stdin is not None
        assert proc.stdout is not None

        _send(
            proc,
            1,
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        )

        _send(
            proc,
            2,
            "tools/call",
            {
                "name": "search_wikipedia",
                "arguments": {"query": "cat distress vocalisation", "limit": 3},
            },
        )

        _send(
            proc,
            3,
            "tools/call",
            {"name": "get_summary", "arguments": {"title": "Cat communication"}},
        )

        _send(
            proc,
            4,
            "tools/call",
            {
                "name": "summarize_article_for_query",
                "arguments": {
                    "title": "Cat communication",
                    "query": "pain vocalization",
                    "max_length": 300,
                },
            },
        )

        time.sleep(4)
        _print_output(proc)


if __name__ == "__main__":
    run_google_maps_mcp()
    run_wikipedia_mcp()
