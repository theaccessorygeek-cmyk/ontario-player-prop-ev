
"""Historical player-prop probability estimates.

This is a transparent empirical baseline, not a complete predictive model.
Observations must be ordered oldest to newest.
"""

import math


DEFAULT_HALF_LIFE = 10
DEFAULT_PRIOR_STRENGTH = 8
MIN_OBSERVATIONS = 20


def estimate_probabilities(
    observations,
    line,
    half_life=DEFAULT_HALF_LIFE,
    prior_strength=DEFAULT_PRIOR_STRENGTH,
    min_observations=MIN_OBSERVATIONS,
):
    """Estimate over, under and push probabilities from game logs."""

    if not isinstance(observations, list):
        raise ValueError("Observations must be a list")

    if len(observations) < min_observations:
        raise ValueError(
            f"At least {min_observations} observations are required"
        )

    if not math.isfinite(float(line)):
        raise ValueError("Line must be finite")

    if half_life <= 0 or prior_strength < 0:
        raise ValueError("Invalid model settings")

    values = []

    for value in observations:
        if isinstance(value, bool):
            raise ValueError("Observations must be numeric")

        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError("Observations must be numeric")

        if not math.isfinite(number):
            raise ValueError("Observations must be finite")

        values.append(number)

    line = float(line)
    weights = [
        0.5 ** ((len(values) - 1 - index) / half_life)
        for index in range(len(values))
    ]

    over_weight = 0.0
    under_weight = 0.0
    push_weight = 0.0
    weighted_total = 0.0
    weight_squared_total = 0.0
    weighted_value_total = 0.0

    raw_over = 0
    raw_under = 0
    raw_push = 0

    for value, weight in zip(values, weights):
        weighted_total += weight
        weight_squared_total += weight * weight
        weighted_value_total += value * weight

        if value > line:
            over_weight += weight
            raw_over += 1
        elif value < line:
            under_weight += weight
            raw_under += 1
        else:
            push_weight += weight
            raw_push += 1

    decisive_weight = over_weight + under_weight

    push_probability = (
        push_weight / weighted_total
        if weighted_total else 0.0
    )

    if decisive_weight:
        smoothed_over_share = (
            over_weight + prior_strength * 0.5
        ) / (decisive_weight + prior_strength)
    else:
        smoothed_over_share = 0.5

    model_over = (
        (1 - push_probability) * smoothed_over_share
    )
    model_under = (
        (1 - push_probability) * (1 - smoothed_over_share)
    )

    effective_sample_size = (
        weighted_total ** 2 / weight_squared_total
        if weight_squared_total else 0.0
    )

    return {
        "model_over_probability": model_over,
        "model_under_probability": model_under,
        "model_push_probability": push_probability,
        "weighted_average": weighted_value_total / weighted_total,
        "observations": len(values),
        "effective_sample_size": effective_sample_size,
        "raw_over": raw_over,
        "raw_under": raw_under,
        "raw_push": raw_push,
        "method": "recency_weighted_empirical_with_beta_shrinkage",
        "half_life_games": half_life,
        "prior_strength": prior_strength,
        "limitations": [
            "Historical baseline only",
            "No injury or lineup adjustment",
            "No minutes or playing-time projection",
            "No opponent or matchup adjustment",
            "Not independently validated for betting use",
        ],
    }
  
