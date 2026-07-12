"""Unit tests for AG-UI message conversion."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# pylint: disable-next=wrong-import-position
from agent.core.messages import to_lc_messages


class _Message:
    def __init__(self, role: str, content: str = ""):
        self.role = role
        self.content = content


def test_state_is_prefixed_to_first_user_message():
    messages = [
        _Message("user", "Book a checkup"),
        _Message("assistant", "Sure"),
    ]

    result = to_lc_messages(
        messages,
        state={
            "owner_profile": {
                "owner_name": "Dickson Lai",
                "owner_phone": "+65 8xxx 9460",
            },
        },
    )

    assert result[0].content.startswith("[state]\nowner_profile:")
    assert "Dickson Lai" in result[0].content
    assert result[0].content.endswith("Book a checkup")
