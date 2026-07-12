"""Small persistence helpers used by the agent runner and API routes."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
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


def list_threads(limit: int = 50) -> list[dict[str, Any]]:
    """List known threads, most recently active first, with a preview of
    the last message and a total message count — enough for a "recent
    chats" list in the app without fetching every message up front."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT
                t.thread_id,
                t.title,
                t.created_at,
                (SELECT COUNT(*) FROM messages m WHERE m.thread_id = t.thread_id)
                    AS message_count,
                (SELECT content FROM messages m WHERE m.thread_id = t.thread_id
                    ORDER BY timestamp DESC LIMIT 1) AS last_message,
                (SELECT timestamp FROM messages m WHERE m.thread_id = t.thread_id
                    ORDER BY timestamp DESC LIMIT 1) AS last_message_at
            FROM threads t
            ORDER BY COALESCE(last_message_at, t.created_at) DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]


def list_pet_profiles() -> list[dict[str, Any]]:
    """Return all stored pet profiles (pet_id, name, species, owner_id)."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT pet_id, owner_id, name, species FROM pet_profiles ORDER BY created_at"
        )
        return [dict(row) for row in cursor.fetchall()]


def list_pets_by_owner(owner_id: str) -> list[dict[str, Any]]:
    """Return all pets belonging to a given owner."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT pet_id, owner_id, name, species, breed, weight_kg, life_stage "
            "FROM pet_profiles WHERE owner_id = ? ORDER BY created_at",
            (owner_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_pet_profile(pet_id: str) -> dict[str, Any] | None:
    """Fetch a pet's stored profile by pet_id."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT pet_id, owner_id, name, species, breed, weight_kg, life_stage,
                   known_conditions, delivery_address, preferred_clinic,
                   preferred_food_brand
            FROM pet_profiles
            WHERE pet_id = ?
            """,
            (pet_id,),
        )
        row = cursor.fetchone()
    return dict(row) if row else None


def upsert_pet_profile(profile: dict[str, Any]) -> None:
    """Create or update a pet's stored profile."""
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO pet_profiles (
                pet_id, owner_id, name, species, breed, weight_kg, life_stage,
                known_conditions, delivery_address, preferred_clinic,
                preferred_food_brand, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(pet_id) DO UPDATE SET
                owner_id=excluded.owner_id,
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
                profile.get("owner_id") or "owner-01",
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


def store_oauth_token(
    thread_id: str, provider: str, token_data: dict[str, Any]
) -> None:
    """Persist OAuth tokens for a provider+thread combination."""
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO oauth_tokens
                (provider, thread_id, scope, access_token, refresh_token,
                 token_expiry, user_email, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                provider,
                thread_id,
                token_data.get("scope"),
                token_data["access_token"],
                token_data.get("refresh_token", ""),
                token_data.get("expiry"),
                token_data.get("user_email"),
            ),
        )


def get_oauth_token(thread_id: str, provider: str) -> dict[str, Any] | None:
    """Retrieve stored OAuth tokens for a provider+thread."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT provider, thread_id, scope, access_token, refresh_token,
                   token_expiry, user_email
            FROM oauth_tokens
            WHERE provider = ? AND thread_id = ?
            """,
            (provider, thread_id),
        )
        row = cursor.fetchone()
    return dict(row) if row else None


def delete_oauth_token(thread_id: str, provider: str) -> None:
    """Remove stored OAuth tokens (e.g. on disconnect)."""
    with get_db() as conn:
        conn.execute(
            "DELETE FROM oauth_tokens WHERE provider = ? AND thread_id = ?",
            (provider, thread_id),
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


def record_pet_moment(
    pet_id: str,
    captured_at: str,
    emotion: str | None,
    species: str,
    image_path: str | None = None,
) -> int:
    """Insert a row into pet_moments (returns the auto-increment id)."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO pet_moments (pet_id, captured_at, emotion, species, image_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (pet_id, captured_at, emotion, species, image_path),
        )
        rowid = cursor.lastrowid
        assert rowid is not None
        return rowid


def _compute_longest_streak(dates: list[date]) -> int:
    longest = 0
    streak = 0
    prev: date | None = None
    for d in dates:
        if prev is None or (d - prev).days == 1:
            streak += 1
        else:
            streak = 1
        longest = max(longest, streak)
        prev = d
    return longest


def _build_month_days(
    day_map: dict[date, list[dict[str, Any]]],
    month_start: date,
) -> list[dict[str, Any]]:
    days_out: list[dict[str, Any]] = []
    for d in sorted(day_map):
        if d.year != month_start.year or d.month != month_start.month:
            continue
        moments = day_map[d]
        emotions = [m["emotion"] for m in moments if m["emotion"]]
        dominant = max(set(emotions), key=emotions.count) if emotions else None

        # Pick the latest image_path from the day's moments
        image_path = None
        for m in reversed(moments):
            if m.get("image_path"):
                image_path = m["image_path"]
                break

        days_out.append(
            {
                "date": d.isoformat(),
                "capture_count": len(moments),
                "dominant_emotion": dominant,
                "species": moments[0]["species"],
                "image_path": image_path,
            }
        )
    return days_out


def get_streak_summary(pet_id: str) -> dict[str, Any]:
    """Compute streak data for a pet and return the frontend contract.

    Returns:
        {
            "current_streak": int,
            "longest_streak": int,
            "month_start": str (ISO date),
            "days": [
                {
                    "date": str,
                    "capture_count": int,
                    "dominant_emotion": str | None,
                    "species": str,
                },
            ],
        }
    """
    today = date.today()
    month_start = date(today.year, today.month, 1)

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT captured_at, emotion, species, image_path
            FROM pet_moments
            WHERE pet_id = ?
            ORDER BY captured_at ASC
            """,
            (pet_id,),
        ).fetchall()

    if not rows:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "month_start": month_start.isoformat(),
            "days": [],
        }

    # Group by date
    day_map: dict[date, list[dict[str, Any]]] = defaultdict(list)
    all_dates: set[date] = set()
    for row in rows:
        d = date.fromisoformat(row["captured_at"])
        day_map[d].append(
            {
                "emotion": row["emotion"],
                "species": row["species"],
                "image_path": row["image_path"],
            }
        )
        all_dates.add(d)

    unique_dates = sorted(all_dates)

    # Current streak (consecutive days ending at or before today)
    current_streak = 0
    d = today
    while d in day_map:
        current_streak += 1
        d -= timedelta(days=1)

    longest_streak = _compute_longest_streak(unique_dates)

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "month_start": month_start.isoformat(),
        "days": _build_month_days(day_map, month_start),
    }
