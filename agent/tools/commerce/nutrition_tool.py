"""
Nutrition / portion-sizing tool — fully functional (not stubbed).

Implements standard veterinary energy-requirement formulas so the agent can
suggest a sensible daily food portion without needing an external API:

  RER (Resting Energy Requirement, kcal/day) = 70 * (weight_kg ** 0.75)
  DER (Daily Energy Requirement)             = RER * activity_factor

Activity factors follow commonly used veterinary nutrition guidelines
(WSAVA-aligned ranges). This is a reasonable default for a recommendation
the user reviews and approves — not a substitute for veterinary advice for
pets with medical conditions.
"""

from typing import Any, Literal

from langchain_core.tools import tool

Species = Literal["dog", "cat"]
LifeStage = Literal["puppy_kitten", "adult", "senior", "pregnant_lactating"]
BodyCondition = Literal["underweight", "ideal", "overweight", "obese"]

# activity_factor multipliers applied to RER to get DER
_ACTIVITY_FACTORS: dict[str, dict[str, float]] = {
    "dog": {
        "puppy_kitten": 3.0,
        "adult": 1.6,
        "senior": 1.4,
        "pregnant_lactating": 3.0,
    },
    "cat": {
        "puppy_kitten": 2.5,
        "adult": 1.2,
        "senior": 1.1,
        "pregnant_lactating": 2.0,
    },
}

# Adjust DER when the pet is over/underweight (encourage gradual correction)
_BODY_CONDITION_ADJUSTMENT: dict[str, float] = {
    "underweight": 1.10,
    "ideal": 1.00,
    "overweight": 0.85,
    "obese": 0.75,
}


@tool
def calculate_daily_portion(
    species: Species,
    weight_kg: float,
    life_stage: LifeStage,
    food_kcal_per_100g: float,
    meals_per_day: int = 2,
    body_condition: BodyCondition = "ideal",
) -> dict[str, Any]:
    """
    Calculate a suggested daily food portion for a pet based on its weight,
    life stage, body condition, and the calorie density of the food on hand.

    Args:
        species: 'dog' or 'cat'.
        weight_kg: Current body weight in kilograms.
        life_stage: 'puppy_kitten', 'adult', 'senior', or 'pregnant_lactating'.
        food_kcal_per_100g: Calorie density of the food, as printed on the
            packaging (kcal per 100g). If unknown, use a reasonable default
            for dry kibble (~350-400 kcal/100g) and flag it to the user.
        meals_per_day: How many meals to split the daily portion across.
        body_condition: 'underweight', 'ideal', 'overweight', or 'obese' —
            used to nudge the recommendation toward a healthy weight.

    Returns:
        A dict with RER, DER, total daily grams, and grams per meal, plus
        the assumptions used so the agent can explain the number to the user.
    """
    if weight_kg <= 0:
        return {"success": False, "error": "weight_kg must be positive."}
    if food_kcal_per_100g <= 0:
        return {"success": False, "error": "food_kcal_per_100g must be positive."}
    if meals_per_day <= 0:
        return {"success": False, "error": "meals_per_day must be positive."}

    activity_factor = _ACTIVITY_FACTORS.get(species, _ACTIVITY_FACTORS["dog"]).get(
        life_stage, 1.6
    )
    condition_adjustment = _BODY_CONDITION_ADJUSTMENT.get(body_condition, 1.0)

    rer_kcal = 70 * (weight_kg**0.75)
    der_kcal = rer_kcal * activity_factor * condition_adjustment

    grams_per_day = (der_kcal / food_kcal_per_100g) * 100
    grams_per_meal = grams_per_day / meals_per_day

    return {
        "success": True,
        "species": species,
        "life_stage": life_stage,
        "body_condition": body_condition,
        "weight_kg": weight_kg,
        "rer_kcal_per_day": round(rer_kcal, 1),
        "activity_factor": activity_factor,
        "condition_adjustment": condition_adjustment,
        "der_kcal_per_day": round(der_kcal, 1),
        "food_kcal_per_100g": food_kcal_per_100g,
        "grams_per_day": round(grams_per_day, 1),
        "meals_per_day": meals_per_day,
        "grams_per_meal": round(grams_per_meal, 1),
        "formula": "RER = 70 * weight_kg^0.75; DER = RER * activity_factor * condition_adjustment",
        "disclaimer": (
            "Estimate based on standard veterinary energy-requirement formulas. "
            "Not a substitute for guidance from a veterinarian, especially for "
            "pets with medical conditions."
        ),
    }


COMMERCE_NUTRITION_TOOLS = [calculate_daily_portion]
