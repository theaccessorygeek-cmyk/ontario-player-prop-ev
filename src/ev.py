
"""Odds conversion and expected-value calculations."""

def american_to_decimal(odds):
    odds = float(odds)
    if odds == 0:
        raise ValueError("American odds cannot be zero")

    if odds > 0:
        return 1 + odds / 100

    return 1 + 100 / abs(odds)


def implied_probability(odds):
    return 1 / american_to_decimal(odds)


def no_vig_probabilities(over_odds, under_odds):
    over = implied_probability(over_odds)
    under = implied_probability(under_odds)

    total = over + under

    return over / total, under / total


def expected_value_per_dollar(
    model_win_probability,
    american_odds,
    push_probability=0.0
):
    if not 0 <= model_win_probability <= 1:
        raise ValueError("Invalid model probability")

    if not 0 <= push_probability <= 1:
        raise ValueError("Invalid push probability")

    if model_win_probability + push_probability > 1:
        raise ValueError("Win and push probabilities exceed 1")

    profit = american_to_decimal(american_odds) - 1

    loss_probability = (
        1 - model_win_probability - push_probability
    )

    return (
        model_win_probability * profit
        - loss_probability
    )
  
