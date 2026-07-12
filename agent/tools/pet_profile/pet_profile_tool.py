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
from backend.services import upsert_pet_profile


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


@tool
def save_pet_profile(
    pet_id: str,
    species: str,
    name: str | None = None,
    breed: str | None = None,
    weight_kg: float | None = None,
    life_stage: str | None = None,
    known_conditions: str | None = None,
    delivery_address: str | None = None,
    preferred_clinic: str | None = None,
    preferred_food_brand: str | None = None,
) -> dict[str, Any]:
    """
    Create or update a pet's stored profile.

    Use this when the user tells you about a new pet or provides updated
    information about an existing one. A minimal profile only needs pet_id
    and species — other fields can be filled in later as the user provides
    more details.

    Args:
        pet_id: A unique identifier for the pet (you can generate one
            with uuid.uuid4() if the user hasn't provided one).
        species: e.g. "Cat", "Dog".
        name: The pet's name.
        breed: The pet's breed.
        weight_kg: The pet's weight in kilograms.
        life_stage: e.g. "Kitten", "Adult", "Senior".
        known_conditions: Any known medical conditions.
        delivery_address: Address for food/litter delivery.
        preferred_clinic: The user's preferred veterinary clinic.
        preferred_food_brand: The pet's preferred food brand.

    Returns:
        A dict with success status and the pet_id.
    """
    upsert_pet_profile(
        {
            "pet_id": pet_id,
            "name": name,
            "species": species,
            "breed": breed,
            "weight_kg": weight_kg,
            "life_stage": life_stage,
            "known_conditions": known_conditions,
            "delivery_address": delivery_address,
            "preferred_clinic": preferred_clinic,
            "preferred_food_brand": preferred_food_brand,
        }
    )
    return {"success": True, "pet_id": pet_id}


PET_PROFILE_TOOLS = [get_pet_profile, save_pet_profile]
