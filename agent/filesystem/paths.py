"""Path helpers for the agent's skills/prompts/subagents directories."""

from pathlib import Path

from ..config import SKILLS_DIR

AGENT_DIR = Path(__file__).resolve().parent.parent


def get_skills_path() -> Path:
    """Absolute path to the skills directory bundled with this package."""
    return AGENT_DIR / SKILLS_DIR


def get_skills_virtual_path() -> str:
    """Virtual path (relative to the backend root) for the skills directory."""
    rel = get_skills_path().relative_to(AGENT_DIR).as_posix()
    return f"/{rel}/"
