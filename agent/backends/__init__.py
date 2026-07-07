"""
Filesystem backend for the agent.

Module 2 doesn't need arbitrary code execution or a writable sandbox — its
tools are all native Python functions or MCP calls. The only filesystem
access the agent needs is *reading* its own `skills/` directory so
`SKILL.md` instructions can be discovered and loaded.

`virtual_mode=True` keeps everything in-memory: even if the model attempts
a write, nothing touches disk.
"""

from deepagents.backends import FilesystemBackend

from ..filesystem import get_skills_path


def build_skills_backend() -> FilesystemBackend:
    """Read-only-in-practice backend rooted at the bundled skills directory."""
    return FilesystemBackend(root_dir=get_skills_path(), virtual_mode=True)
