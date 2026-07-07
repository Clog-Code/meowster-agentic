---
name: supply-ordering
description: Use whenever a perception event's detected_workflow is supply_shortage, or the owner mentions running low on food/water. Covers sourcing, nutrition-based portioning, and the ordering workflow.
---

# Supply Ordering Skill

## When to use

- `detected_workflow: supply_shortage` in a `[perception-event]` block.
- The owner mentions running low on pet food, treats, or supplies.

## Workflow

1. **Delegate to `supply-inventory`** with: pet_id, species, and which
   resource is low (food/water). If water is low and IoT dispensers exist
   in the wider system, note that this subagent only handles the
   *food/commerce* side — water-dispenser control belongs to Module 3
   (IoT), not this agent.
2. **Review the nutrition calculation and shortlist** the subagent
   returns. Sanity-check that the recommended quantity/frequency makes
   sense before approving an order (e.g. don't let a bag size wildly
   exceed a reasonable 2-4 week supply).
3. **Confirm with the owner before ordering** unless they've already said
   "just order it" — summarize retailer, item, quantity, price, and ETA.
4. **Report status** clearly, noting whether `place_order` returned
   `"stubbed"` (drafted, not a real purchase) or a real confirmation.

## Hard rules

- Never state a price or ETA that didn't come from an actual tool result.
- Never tell the owner payment went through unless the order tool result
  says so with a real (non-stubbed) status.
- If the pet's profile lists a `preferred_food_brand`, prefer it over an
  unfamiliar brand unless it's unavailable everywhere checked.
