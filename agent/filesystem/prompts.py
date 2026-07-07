"""Prompt template loader."""

from pathlib import Path

from ..config import PROMPTS_DIR
from .paths import AGENT_DIR


def load_prompt(name: str) -> str:
    """Load a prompt template file (without the .md extension) as text."""
    prompt_path = Path(AGENT_DIR) / PROMPTS_DIR / f"{name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()


def get_initializer_prompt(tool_docs: str = "") -> str:
    """Load and format the orchestrator's system prompt."""
    prompt = load_prompt("initializer_prompt")
    return prompt.format(tool_docs=tool_docs)


def get_thread_prompt() -> str:
    """Load the thread title generation prompt."""
    return load_prompt("thread_title_prompt")
