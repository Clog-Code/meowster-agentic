"""SQLite connection + schema management for the backend."""

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


@contextmanager
def get_db():
    """Context-managed SQLite connection; commits on success, closes always."""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
