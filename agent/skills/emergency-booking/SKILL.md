---
name: emergency-booking
description: Use whenever a perception event's detected_workflow is health_emergency, or the owner describes symptoms/injury/distress. Covers clinic discovery, urgency triage, and the appointment request workflow.
---

# Emergency Booking Skill

## When to use

- `detected_workflow: health_emergency` in a `[perception-event]` block.
- The owner directly describes symptoms, injury, or distress.

## Workflow

1. **Triage first.** Before spawning `vet-emergency`, decide roughly how
   urgent this is from the health_flags/emotion/notes given:
   - Severe (collapse, seizure, suspected poisoning, uncontrolled bleeding):
     tell the owner this needs immediate in-person or emergency-line care,
     and still proceed to find the nearest clinic fast.
   - Moderate (limping, vomiting, unusual lethargy): proceed to full
     discovery + booking workflow below.
   - Mild/ambiguous (e.g. a single distress vocalization with no other
     signal): consider using `pet-info-lookup` first to check whether the
     behavior is typical for the species/breed before escalating.
2. **Delegate to `vet-emergency`** with: pet_id, species, symptoms/flags,
   and the owner's location if known. Ask the orchestrator's own context
   (not the subagent) for location if missing — don't guess a city.
3. **Review the subagent's shortlist and communication result.** Before
   telling the owner anything was booked, check whether the result was
   `"stubbed"` — if so, present it as a *drafted* request pending real
   integration, not a confirmed appointment.
4. **Summarize for the owner**: clinic name/address/contact, proposed time,
   what was sent (call/email/WhatsApp) and its actual status, and a clear
   next step (e.g. "I've drafted this request — want me to send it once
   it's wired up, or would you rather call them yourself right now?").

## Hard rules

- Never tell the owner an appointment is confirmed unless a tool result
  says so with a real (non-stubbed) status.
- Never skip triage — even a mild signal should get at least a one-line
  urgency assessment before any tool call.
