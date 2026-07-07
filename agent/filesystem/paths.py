"""Path helpers for the agent's skills/prompts/subagents directories."""

from pathlib import Path

from ..config import SKILLS_DIR

AGENT_DIR = Path(__file__).resolve().parent.parent


def get_skills_path() -> Path:
    """Absolute path to the skills directory bundled with this package."""
    return AGENT_DIR / SKILLS_DIR


def build_skills_virtual_path() -> str:
    """Stable virtual route deepagents uses to mount the skills directory."""
    normalized = SKILLS_DIR.replace("\\", "/").strip("/")
    return f"/{normalized or 'skills'}/"
