"""
Filesystem backend for reading the bundled skills/ directory.

The agent reads SKILL.md files from the skills directory via the
deepagents skills middleware.  No sandbox or writable filesystem is needed,
so ``virtual_mode=True`` keeps everything in-memory (even if the model
attempts a write, nothing touches disk).
"""

from pathlib import Path

from deepagents.backends import FilesystemBackend

AGENT_DIR = Path(__file__).resolve().parent.parent


def build_skills_backend() -> FilesystemBackend:
    """Read-only-in-practice backend rooted at the agent package root."""
    return FilesystemBackend(root_dir=AGENT_DIR, virtual_mode=True)
