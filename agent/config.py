"""Shared configuration values for the agent runtime."""

import os

# ---------------------------------------------------------------------------
# LLM configuration defaults
# ---------------------------------------------------------------------------
LLM_DEFAULTS = {
    "temperature": 0.2,
    "recursion_limit": 200,
    "max_tokens": 4096,
}

MODE_THINKING_GENERAL = {
    "temperature": 0.6,
    "top_p": 0.95,
    "top_k": 20,
    "min_p": 0.0,
    "presence_penalty": 0.0,
    "repetition_penalty": 1.0,
}

MODE_INSTRUCT = {
    "temperature": 0.7,
    "top_p": 0.80,
    "top_k": 20,
    "min_p": 0.0,
    "presence_penalty": 1.5,
    "repetition_penalty": 1.0,
}

# ---------------------------------------------------------------------------
# Filesystem layout (relative to the `agent/` package)
# ---------------------------------------------------------------------------
SKILLS_DIR = "skills/"
PROMPTS_DIR = "prompts/"
SUBAGENTS_DIR = "subagents/"

# ---------------------------------------------------------------------------
# MCP self-discovery
# ---------------------------------------------------------------------------
# Comma-separated list of server short-names, e.g. "maps,wikipedia".
# Each name must have MCP_<NAME>_URL (or _COMMAND for stdio) + MCP_<NAME>_TRANSPORT
# defined in the environment. See .env.example for the full contract.
MCP_SERVERS_ENV = "MCP_SERVERS"


def get_mcp_server_names() -> list[str]:
    """Read the list of MCP server short-names configured for self-discovery."""
    raw = os.getenv(MCP_SERVERS_ENV, "")
    return [name.strip().lower() for name in raw.split(",") if name.strip()]
