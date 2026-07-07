"""
Perception intake.

Module 1 (a teammate's camera/audio ML pipeline) does NOT feed raw video or
audio into this service. It posts a structured JSON summary to
`POST /perception` on this FastAPI app, already reduced to text by their ML
models. This module's only job is to:

  1. Validate/normalize that payload into a `PerceptionEvent`.
  2. Classify which workflow it implies (health emergency / supply shortage /
     informational-only).
  3. Turn it into the first user-role message handed to the orchestrator, so
     the rest of the system (subagents, MCP tools, AG-UI streaming) behaves
     exactly as if a person had typed a request.

Expected payload shape (see backend/main.py's Pydantic model for the wire
contract):

    {
      "pet_id": "buddy-01",
      "species": "dog",
      "emotion": "distress",
      "emotion_confidence": 0.87,
      "health_flags": ["limping", "whining"],
      "food_level": "empty",       # "full" | "low" | "empty" | null
      "water_level": "ok",         # "ok" | "low" | "empty" | null
      "notes": "Detected via audio distress classifier + posture anomaly",
      "timestamp": "2026-07-07T09:15:00Z"
    }
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class WorkflowKind(str, Enum):
    """The autonomous-intervention workflow triggered by a perception event."""

    HEALTH_EMERGENCY = "health_emergency"
    SUPPLY_SHORTAGE = "supply_shortage"
    INFO_ONLY = "info_only"


# Emotion/health labels from the ML module that should trigger the health
# workflow. Extend this list as the ML teammate's taxonomy grows — it's data,
# not logic, so no other code needs to change.
_HEALTH_TRIGGER_LABELS = {
    "distress",
    "pain",
    "injury",
    "lethargy",
    "seizure",
    "vomiting",
    "abnormal_gait",
}


@dataclass
class PerceptionEvent:
    """Normalised representation of a Module-1 perception payload."""

    pet_id: str
    species: str
    emotion: str | None = None
    emotion_confidence: float | None = None
    health_flags: list[str] = field(default_factory=list)
    food_level: str | None = None
    water_level: str | None = None
    notes: str | None = None
    timestamp: str | None = None

    def classify(self) -> WorkflowKind:
        """Decide which autonomous-intervention workflow this event implies."""
        emotion_flagged = (self.emotion or "").lower() in _HEALTH_TRIGGER_LABELS
        has_health_flags = bool(self.health_flags)

        if emotion_flagged or has_health_flags:
            return WorkflowKind.HEALTH_EMERGENCY

        if (self.food_level or "").lower() in {"low", "empty"} or (
            self.water_level or ""
        ).lower() in {"low", "empty"}:
            return WorkflowKind.SUPPLY_SHORTAGE

        return WorkflowKind.INFO_ONLY

    def to_orchestrator_message(self) -> str:
        """
        Render this event as a natural-language message for the orchestrator's
        first turn, so downstream prompting/subagent logic is workflow-based
        rather than needing to parse raw JSON itself.
        """
        workflow = self.classify()

        lines = [
            "[perception-event]",
            f"pet_id: {self.pet_id}",
            f"species: {self.species}",
            f"detected_workflow: {workflow.value}",
        ]
        if self.emotion:
            confidence = (
                f" (confidence {self.emotion_confidence:.2f})"
                if self.emotion_confidence is not None
                else ""
            )
            lines.append(f"emotion: {self.emotion}{confidence}")
        if self.health_flags:
            lines.append(f"health_flags: {', '.join(self.health_flags)}")
        if self.food_level:
            lines.append(f"food_level: {self.food_level}")
        if self.water_level:
            lines.append(f"water_level: {self.water_level}")
        if self.notes:
            lines.append(f"notes: {self.notes}")
        if self.timestamp:
            lines.append(f"observed_at: {self.timestamp}")

        lines.append(
            "\nUsing the detected workflow above, follow the matching skill "
            "(emergency-booking or supply-ordering) and delegate to the "
            "matching subagent. If detected_workflow is info_only, just "
            "summarize the pet's state for the user — no autonomous action "
            "is needed."
        )
        return "\n".join(lines)


def parse_perception_payload(payload: dict) -> PerceptionEvent:
    """Build a PerceptionEvent from a raw dict (already-validated by FastAPI)."""
    return PerceptionEvent(
        pet_id=payload["pet_id"],
        species=payload["species"],
        emotion=payload.get("emotion"),
        emotion_confidence=payload.get("emotion_confidence"),
        health_flags=payload.get("health_flags") or [],
        food_level=payload.get("food_level"),
        water_level=payload.get("water_level"),
        notes=payload.get("notes"),
        timestamp=payload.get("timestamp"),
    )
