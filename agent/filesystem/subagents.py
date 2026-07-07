"""
Subagent configuration loader.

Each subagent lives in `agent/subagents/<name>/AGENT.md` with YAML
frontmatter (name, description, tools) followed by its system prompt.

The `tools:` field is a comma-separated list of tool-group keys. These keys
are resolved against whatever `core.registry.build_tool_groups()` returns —
which includes native groups ("communication", "commerce", "calendar",
"pet_profile") AND every MCP server name discovered from .env ("maps",
"wikipedia", or any plugin added later). Adding a new MCP plugin therefore
never requires touching this file — just reference its server name in an
AGENT.md's `tools:` field.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from langchain_core.tools import BaseTool

from ..config import SUBAGENTS_DIR
from .paths import AGENT_DIR


def _load_subagent_data(agent_dir: Path) -> tuple[dict[str, Any], str]:
    agent_file = agent_dir / "AGENT.md"
    if not agent_file.exists():
        raise FileNotFoundError(f"Subagent configuration missing: {agent_file}")

    content = agent_file.read_text(encoding="utf-8")
    parts = content.split("---")
    if len(parts) < 3:
        raise ValueError(
            f"Invalid frontmatter format in {agent_file}. Expected '---metadata---prompt'."
        )

    metadata_raw = parts[1].strip()
    system_prompt = "---".join(parts[2:]).strip()
    return yaml.safe_load(metadata_raw), system_prompt


def build_subagent_configs(
    tool_groups: dict[str, list[BaseTool]],
) -> list[dict[str, Any]]:
    """
    Discover every subagent directory and parse its AGENT.md, resolving its
    declared tool groups against the live `tool_groups` mapping (native +
    MCP-discovered).
    """
    subagent_root = Path(AGENT_DIR) / SUBAGENTS_DIR
    if not subagent_root.exists():
        raise FileNotFoundError(f"Subagents directory not found: {subagent_root}")

    configs: list[dict[str, Any]] = []

    for agent_dir in sorted(subagent_root.iterdir()):
        if not agent_dir.is_dir() or agent_dir.name.startswith("."):
            continue

        try:
            metadata, system_prompt = _load_subagent_data(agent_dir)
        except (ValueError, yaml.YAMLError) as e:
            print(f"[subagents] skipping {agent_dir.name}: {e}")
            continue

        tools_raw = metadata.get("tools", "")
        tool_keys = (
            tools_raw
            if isinstance(tools_raw, list)
            else [t.strip() for t in tools_raw.split(",") if t.strip()]
        )

        assigned_tools: list[BaseTool] = []
        for key in tool_keys:
            group = tool_groups.get(key)
            if group is None:
                print(
                    f"[subagents] '{agent_dir.name}' requested unknown tool "
                    f"group '{key}' — is it in MCP_SERVERS or a native group? Skipping."
                )
                continue
            assigned_tools.extend(group)

        configs.append(
            {
                "name": metadata.get("name", agent_dir.name),
                "description": metadata.get("description", ""),
                "system_prompt": system_prompt,
                "tools": assigned_tools,
            }
        )

    return configs
