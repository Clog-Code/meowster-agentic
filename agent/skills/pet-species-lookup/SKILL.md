---
name: pet-species-lookup
description: Use when you need species/breed reference context to judge whether a detected behavior or symptom is actually abnormal, or to answer a general care question, before deciding whether to escalate to the emergency-booking or supply-ordering skill.
---

# Pet Species Lookup Skill

## When to use

- A perception event's signal is ambiguous (e.g. a single vocalization
  flagged "distress" with low confidence, or a food/water level marked
  "low" for a species whose baseline consumption you're unsure about).
- The owner asks a general species/breed care question.

## Workflow

1. Delegate to `pet-info-lookup` with a specific, answerable question
   (e.g. "Do Siamese cats commonly vocalize more than other breeds?"),
   not just the raw perception event.
2. Use the answer to decide: does this genuinely warrant the
   emergency-booking or supply-ordering skill, or is it within normal
   range for the species/breed?
3. If still ambiguous after the lookup, err toward the lighter-weight
   action (e.g. flag it to the owner for confirmation rather than
   auto-booking an appointment) rather than guessing.

## Hard rules

- This skill never takes action on its own — it only informs the
  triage decision made in `emergency-booking` or `supply-ordering`.
- Don't treat the lookup's answer as medical clearance — if health_flags
  are present alongside the ambiguous signal, still proceed with
  emergency-booking's triage step.
