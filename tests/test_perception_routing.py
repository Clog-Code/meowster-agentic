"""Unit tests for perception-event classification (no network/LLM needed)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# pylint: disable-next=wrong-import-position
from agent.core.perception import WorkflowKind, parse_perception_payload


def test_health_flags_trigger_emergency():
    """Health flags should produce a HEALTH_EMERGENCY classification."""
    event = parse_perception_payload(
        {"pet_id": "p1", "species": "dog", "health_flags": ["limping"]}
    )
    assert event.classify() == WorkflowKind.HEALTH_EMERGENCY


def test_distress_emotion_triggers_emergency():
    """Distress emotion with high confidence triggers emergency."""
    event = parse_perception_payload(
        {
            "pet_id": "p1",
            "species": "cat",
            "emotion": "distress",
            "emotion_confidence": 0.9,
        }
    )
    assert event.classify() == WorkflowKind.HEALTH_EMERGENCY


def test_empty_food_triggers_supply_shortage():
    """Empty food level triggers supply shortage."""
    event = parse_perception_payload(
        {"pet_id": "p1", "species": "dog", "food_level": "empty"}
    )
    assert event.classify() == WorkflowKind.SUPPLY_SHORTAGE


def test_low_water_triggers_supply_shortage():
    """Low water level triggers supply shortage."""
    event = parse_perception_payload(
        {"pet_id": "p1", "species": "dog", "water_level": "low"}
    )
    assert event.classify() == WorkflowKind.SUPPLY_SHORTAGE


def test_normal_state_is_info_only():
    """Normal state with no flags produces INFO_ONLY."""
    event = parse_perception_payload(
        {
            "pet_id": "p1",
            "species": "dog",
            "emotion": "playful",
            "food_level": "full",
            "water_level": "ok",
        }
    )
    assert event.classify() == WorkflowKind.INFO_ONLY


def test_health_flags_take_priority_over_supply():
    """Health flags override supply shortages in priority."""
    event = parse_perception_payload(
        {
            "pet_id": "p1",
            "species": "dog",
            "health_flags": ["vomiting"],
            "food_level": "empty",
        }
    )
    assert event.classify() == WorkflowKind.HEALTH_EMERGENCY


def test_orchestrator_message_mentions_workflow():
    """Orchestrator message contains the detected workflow type and pet id."""
    event = parse_perception_payload(
        {"pet_id": "buddy-01", "species": "dog", "health_flags": ["limping"]}
    )
    message = event.to_orchestrator_message()
    assert "detected_workflow: health_emergency" in message
    assert "buddy-01" in message
