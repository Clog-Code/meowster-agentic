"""Owner profile lookup tool — reads from the owner_profiles SQLite table."""

from typing import Any

from langchain_core.tools import tool

from backend.db import get_db


@tool
def get_owner_profile(owner_id: str = "owner-01") -> dict[str, Any]:
    """
    Look up the pet owner's stored profile: name, phone, and address.

    Call this whenever the user asks about their own name, contact details,
    or address — do NOT read those values from the [state] block.

    Args:
        owner_id: The owner's unique identifier (defaults to "owner-01").

    Returns:
        The stored owner profile dict, or an error if not found.
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT owner_id, name, phone, address FROM owner_profiles WHERE owner_id = ?",
            (owner_id,),
        ).fetchone()

    if row is None:
        return {"success": False, "error": f"No owner profile found for '{owner_id}'."}
    return {"success": True, "profile": dict(row)}


OWNER_PROFILE_TOOLS = [get_owner_profile]
