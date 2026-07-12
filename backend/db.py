"""SQLite connection + schema management for the backend."""

import datetime as _dt
import uuid
import sqlite3
from contextlib import contextmanager

from .config import DATABASE_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS owner_profiles (
    owner_id    TEXT PRIMARY KEY,
    name        TEXT,
    phone       TEXT,
    address     TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pet_profiles (
    pet_id                TEXT PRIMARY KEY,
    owner_id              TEXT REFERENCES owner_profiles(owner_id),
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

CREATE TABLE IF NOT EXISTS pet_moments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id      TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    emotion     TEXT,
    species     TEXT NOT NULL,
    image_path  TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pet_moments_pet_date
    ON pet_moments(pet_id, captured_at);

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
        _migrate(conn)
        _seed_owner_profiles(conn)
        _seed_pet_profiles(conn)
        _seed_pet_moments(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    """Apply additive migrations to an existing database."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(pet_profiles)")}
    if "owner_id" not in cols:
        conn.execute(
            "ALTER TABLE pet_profiles ADD COLUMN owner_id TEXT REFERENCES owner_profiles(owner_id)"
        )


_SEED_OWNERS = [
    {
        "owner_id": "owner-01",
        "name": "Dickson Lai",
        "phone": "+60 14-xxx 9460",
        "address": "14000 Bukit Mertajam, Pulau Pinang",
    },
]


def _seed_owner_profiles(conn) -> None:
    for owner in _SEED_OWNERS:
        conn.execute(
            "INSERT OR IGNORE INTO owner_profiles (owner_id, name, phone, address) "
            "VALUES (?, ?, ?, ?)",
            (owner["owner_id"], owner["name"], owner["phone"], owner["address"]),
        )


_SEED_PROFILES = [
    {
        "pet_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "mochi")),
        "owner_id": "owner-01",
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
        "owner_id": "owner-01",
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
                pet_id, owner_id, name, species, breed, weight_kg, life_stage,
                known_conditions, delivery_address, preferred_clinic,
                preferred_food_brand
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile["pet_id"],
                profile["owner_id"],
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


def _seed_pet_moments(conn) -> None:
    """Insert sample pet-moment data for streak history (once per pet_id)."""
    seeded = {
        row[0]
        for row in conn.execute("SELECT DISTINCT pet_id FROM pet_moments").fetchall()
    }

    if {
        "pet-01",
        str(uuid.uuid5(uuid.NAMESPACE_DNS, "mochi")),
        str(uuid.uuid5(uuid.NAMESPACE_DNS, "luna")),
    }.issubset(seeded):
        return

    today = _dt.date.today()
    emotions = ["curious", "happy", "playful", "calm", "normal", "surprised", "rested"]

    def _insert(pet_id: str, days_ago: int, emotion: str, species: str) -> None:
        d = (today - _dt.timedelta(days=days_ago)).isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO pet_moments (pet_id, captured_at, emotion, species) "
            "VALUES (?, ?, ?, ?)",
            (pet_id, d, emotion, species),
        )

    # Default frontend pet_id ('pet-01') — rich streak data
    for offset in range(10):  # 10-day ongoing streak
        _insert("pet-01", offset, emotions[offset % len(emotions)], "Cat")
    _insert("pet-01", 12, "happy", "Cat")
    _insert("pet-01", 13, "playful", "Cat")
    _insert("pet-01", 16, "calm", "Cat")
    _insert("pet-01", 17, "curious", "Cat")
    _insert("pet-01", 18, "normal", "Cat")
    _insert("pet-01", 21, "surprised", "Cat")
    _insert("pet-01", 22, "rested", "Cat")
    _insert("pet-01", 25, "curious", "Cat")
    _insert("pet-01", 26, "happy", "Cat")
    _insert("pet-01", 29, "playful", "Cat")

    # Mochi — 12-day active streak then 2-day gap then ongoing
    mochi_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "mochi"))
    if mochi_id not in seeded:
        for offset in range(14):  # days 0-13 (today back 13 days)
            if 4 <= offset <= 5:
                continue  # gap on days -4, -5
            _insert(mochi_id, offset, emotions[offset % len(emotions)], "Cat")
        _insert(mochi_id, 17, "curious", "Cat")
        _insert(mochi_id, 18, "happy", "Cat")
        _insert(mochi_id, 21, "playful", "Cat")
        _insert(mochi_id, 22, "calm", "Cat")
        _insert(mochi_id, 23, "normal", "Cat")
        _insert(mochi_id, 27, "surprised", "Cat")
        _insert(mochi_id, 28, "rested", "Cat")
        _insert(mochi_id, 29, "curious", "Cat")

    # Luna — 5-day ongoing streak
    luna_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "luna"))
    if luna_id not in seeded:
        for offset in range(5):  # past 5 days
            _insert(luna_id, offset, emotions[(offset + 2) % len(emotions)], "Cat")
        _insert(luna_id, 10, "happy", "Cat")
        _insert(luna_id, 11, "playful", "Cat")
        _insert(luna_id, 12, "calm", "Cat")
        _insert(luna_id, 15, "curious", "Cat")
        _insert(luna_id, 16, "normal", "Cat")
        _insert(luna_id, 17, "happy", "Cat")
        _insert(luna_id, 20, "playful", "Cat")
        _insert(luna_id, 21, "surprised", "Cat")
        _insert(luna_id, 24, "rested", "Cat")
        _insert(luna_id, 25, "curious", "Cat")
        _insert(luna_id, 28, "happy", "Cat")
        _insert(luna_id, 29, "calm", "Cat")


@contextmanager
def get_db():
    """Context-managed SQLite connection; commits on success, closes always."""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
