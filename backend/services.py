"""Small persistence helpers used by the agent runner and API routes."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from .db import get_db


def ensure_thread(thread_id: str) -> None:
    """Create a conversation thread if it doesn't already exist."""
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO threads (thread_id) VALUES (?)",
            (thread_id,),
        )


def persist_message(message_id: str, thread_id: str, role: str, content: str) -> None:
    """Persist a chat message to the database."""
    ensure_thread(thread_id)
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO messages (message_id, thread_id, role, content, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (message_id, thread_id, role, content, datetime.now(UTC).isoformat()),
        )


def get_thread_messages(thread_id: str) -> list[dict[str, Any]]:
    """Retrieve all messages for a given thread, ordered by timestamp."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT message_id, role, content, timestamp FROM messages "
            "WHERE thread_id = ? ORDER BY timestamp ASC",
            (thread_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def upsert_pet_profile(profile: dict[str, Any]) -> None:
    """Create or update a pet's stored profile."""
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO pet_profiles (
                pet_id, name, species, breed, weight_kg, life_stage,
                known_conditions, delivery_address, preferred_clinic,
                preferred_food_brand, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(pet_id) DO UPDATE SET
                name=excluded.name,
                species=excluded.species,
                breed=excluded.breed,
                weight_kg=excluded.weight_kg,
                life_stage=excluded.life_stage,
                known_conditions=excluded.known_conditions,
                delivery_address=excluded.delivery_address,
                preferred_clinic=excluded.preferred_clinic,
                preferred_food_brand=excluded.preferred_food_brand,
                updated_at=datetime('now')
            """,
            (
                profile["pet_id"],
                profile.get("name"),
                profile["species"],
                profile.get("breed"),
                profile.get("weight_kg"),
                profile.get("life_stage"),
                profile.get("known_conditions"),
                profile.get("delivery_address"),
                profile.get("preferred_clinic"),
                profile.get("preferred_food_brand"),
            ),
        )


def record_perception_event(
    pet_id: str, payload: dict[str, Any], workflow: str, thread_id: str
) -> str:
    """Log a perception event for audit/history."""
    event_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO perception_events (event_id, pet_id, payload, workflow, thread_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_id, pet_id, json.dumps(payload), workflow, thread_id),
        )
    return event_id
