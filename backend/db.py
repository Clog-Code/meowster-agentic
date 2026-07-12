"""SQLite connection + schema management for the backend."""

import uuid
import sqlite3
from contextlib import contextmanager

from .config import DATABASE_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pet_profiles (
    pet_id                TEXT PRIMARY KEY,
    name                  TEXT,
    species               TEXT NOT NULL,
    breed                 TEXT,
    weight_kg             REAL,
    life_stage            TEXT,
    known_conditions       TEXT,
    delivery_address      TEXT,
    preferred_clinic      TEXT,
    preferred_food_brand  TEXT,
    created_at            TEXT DEFAULT (datetime('now')),
    updated_at            TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS threads (
    thread_id   TEXT PRIMARY KEY,
    title       TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    message_id  TEXT PRIMARY KEY,
    thread_id   TEXT NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT,
    timestamp   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS perception_events (
    event_id    TEXT PRIMARY KEY,
    pet_id      TEXT NOT NULL,
    payload     TEXT NOT NULL,
    workflow    TEXT NOT NULL,
    thread_id   TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS oauth_tokens (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    provider       TEXT NOT NULL,
    thread_id      TEXT NOT NULL,
    scope          TEXT,
    access_token   TEXT NOT NULL,
    refresh_token  TEXT NOT NULL,
    token_expiry   TEXT,
    user_email     TEXT,
    created_at     TEXT DEFAULT (datetime('now')),
    updated_at     TEXT DEFAULT (datetime('now')),
    UNIQUE(provider, thread_id)
);
"""


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create tables if they don't already exist. Call once at startup."""
    with _connect() as conn:
        conn.executescript(_SCHEMA)
        _seed_pet_profiles(conn)


_SEED_PROFILES = [
    {
        "pet_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "mochi")),
        "name": "Mochi",
        "species": "Cat",
        "breed": "Domestic Shorthair",
        "weight_kg": 4.2,
        "life_stage": "Adult",
        "known_conditions": "None",
        "delivery_address": "123 Pet Street, NY 10001",
        "preferred_clinic": "Happy Paws Vet Clinic",
        "preferred_food_brand": "Whiskas",
    },
    {
        "pet_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "luna")),
        "name": "Luna",
        "species": "Cat",
        "breed": "Persian",
        "weight_kg": 3.8,
        "life_stage": "Kitten",
        "known_conditions": "None",
        "delivery_address": "123 Pet Street, NY 10001",
        "preferred_clinic": "Happy Paws Vet Clinic",
        "preferred_food_brand": "Royal Canin",
    },
]


def _seed_pet_profiles(conn) -> None:
    """Insert default pet profiles if they don't already exist."""
    for profile in _SEED_PROFILES:
        conn.execute(
            """
            INSERT OR IGNORE INTO pet_profiles (
                pet_id, name, species, breed, weight_kg, life_stage,
                known_conditions, delivery_address, preferred_clinic,
                preferred_food_brand
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile["pet_id"],
                profile["name"],
                profile["species"],
                profile["breed"],
                profile["weight_kg"],
                profile["life_stage"],
                profile["known_conditions"],
                profile["delivery_address"],
                profile["preferred_clinic"],
                profile["preferred_food_brand"],
            ),
        )


@contextmanager
def get_db():
    """Context-managed SQLite connection; commits on success, closes always."""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
