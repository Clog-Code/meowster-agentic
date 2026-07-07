"""
Pet profile lookup tool — functional (not stubbed).

Reads the pet's stored profile (species, breed, weight, known conditions,
delivery address, preferred clinic, etc.) from the backend SQLite database
so subagents don't have to ask the user to repeat static information on
every run.
"""

from typing import Any

from langchain_core.tools import tool

from backend.db import get_db


@tool
def get_pet_profile(pet_id: str) -> dict[str, Any]:
    """
    Look up a pet's stored profile: species, breed, weight, known medical
    conditions, delivery address, and preferred clinic (if any).

    Args:
        pet_id: The pet's unique identifier, as sent by the perception
            event from the ML module.

    Returns:
        The stored profile dict, or an error if no profile exists yet for
        this pet_id (in which case, ask the user for the missing details).
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT pet_id, name, species, breed, weight_kg, life_stage,
                   known_conditions, delivery_address, preferred_clinic,
                   preferred_food_brand
            FROM pet_profiles
            WHERE pet_id = ?
            """,
            (pet_id,),
        )
        row = cursor.fetchone()

    if row is None:
        return {
            "success": False,
            "error": f"No stored profile for pet_id '{pet_id}'. Ask the user for "
            "species, weight, and any known conditions before proceeding.",
        }

    return {"success": True, "profile": dict(row)}


PET_PROFILE_TOOLS = [get_pet_profile]
