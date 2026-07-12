"""Unit tests for the owner_profile_tool module."""

import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# pylint: disable-next=wrong-import-position
from agent.tools.owner_profile import owner_profile_tool


def test_get_owner_profile_returns_linked_pets(monkeypatch):
    """Test that get_owner_profile returns the linked pets for a given owner profile."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE owner_profiles (
            owner_id TEXT PRIMARY KEY, name TEXT, phone TEXT, address TEXT
        );
        CREATE TABLE pet_profiles (
            pet_id TEXT PRIMARY KEY, owner_id TEXT, name TEXT, species TEXT,
            breed TEXT, created_at TEXT
        );
        INSERT INTO owner_profiles VALUES ('owner-01', 'Dickson', '123', 'Penang');
        INSERT INTO pet_profiles VALUES (
            'pet-01', 'owner-01', 'Mochi', 'Cat', 'Domestic Shorthair',
            '2026-01-01'
        );
        """
    )

    @contextmanager
    def fake_get_db():
        yield conn

    monkeypatch.setattr(owner_profile_tool, "get_db", fake_get_db)

    result = owner_profile_tool.get_owner_profile.invoke({"owner_id": "owner-01"})

    assert result["success"] is True
    assert result["profile"]["owner_id"] == "owner-01"
    assert result["pets"] == [
        {
            "pet_id": "pet-01",
            "name": "Mochi",
            "species": "Cat",
            "breed": "Domestic Shorthair",
        }
    ]
