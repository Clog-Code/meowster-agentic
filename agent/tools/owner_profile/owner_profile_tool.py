"""Owner profile lookup tool — reads from the owner_profiles SQLite table."""

from typing import Any

from langchain_core.tools import tool

from backend.db import get_db


@tool
def get_owner_profile(owner_id: str = "owner-01") -> dict[str, Any]:
    """
    Look up the pet owner's stored profile: name, phone, and address,
    plus all pets linked to this owner.

    Call this whenever the user asks about their own name, contact details,
    address, or what pets they have — do NOT read those values from the [state] block.

    Args:
        owner_id: The owner's unique identifier (defaults to "owner-01").

    Returns:
        The stored owner profile dict including a "pets" list, or an error if not found.
    """
    with get_db() as conn:
        owner_row = conn.execute(
            "SELECT owner_id, name, phone, address FROM owner_profiles WHERE owner_id = ?",
            (owner_id,),
        ).fetchone()

        if owner_row is None:
            return {"success": False, "error": f"No owner profile found for '{owner_id}'."}

        pets = conn.execute(
            "SELECT pet_id, name, species, breed FROM pet_profiles WHERE owner_id = ? ORDER BY created_at",
            (owner_id,),
        ).fetchall()

    return {
        "success": True,
        "profile": dict(owner_row),
        "pets": [dict(p) for p in pets],
    }


OWNER_PROFILE_TOOLS = [get_owner_profile]
