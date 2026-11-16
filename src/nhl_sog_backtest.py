
"""Walk-forward forecasting test for NHL shots on goal.

Uses only earlier games to forecast the next game's shots.
This evaluates statistical forecasting accuracy, not betting ROI.
"""

import argparse
import csv
import json
import math
from collections import defaultdict


DEFAULT_HALF_LIFE = 10
DEFAULT_MIN_OBSERVATIONS = 20


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def weighted_average(values, half_life):
    if not values:
        raise ValueError("At least one historical value is required")

    if half_life <= 0:
        raise ValueError("Half-life must be positive")

    weights = [
        0.5 ** ((len(values) - 1 - index) / half_life)
        for index in range(len(values))
    ]

    return sum(
        value * weight
        for value, weight in zip(values, weights)
    ) / sum(weights)


def run_backtest(
    rows,
    min_observations=DEFAULT_MIN_OBSERVATIONS,
    half_life=DEFAULT_HALF_LIFE,
):
    if not isinstance(rows, list):
        raise ValueError("Rows must be a list")

    if (
        isinstance(min_observations, bool)
        or not isinstance(min_observations, int)
        or min_observations < 1
    ):
        raise ValueError("Minimum observations must be positive")

    if (
        isinstance(half_life, bool)
        or not isinstance(half_life, (int, float))
        or not math.isfinite(half_life)
        or half_life <= 0
    ):
        raise ValueError("Half-life must be positive and finite")

    groups = defaultdict(list)

    for row in rows:
        try:
            game_date = row["game_date"]
            game_id = str(row["game_id"])
            player = str(row["player"]).strip()
            actual = int(row["shots_on_goal"])

            from datetime import date
            date.fromisoformat(game_date)

        except (KeyError, TypeError, ValueError):
            raise ValueError(
                "Each row needs valid game_date, game_id, "
                "player and shots_on_goal fields"
            )

        if not player or not game_id:
            raise ValueError("Player and game ID cannot be blank")

        if actual < 0:
            raise ValueError("Shots on goal cannot be negative")

        groups[player].append((game_date, game_id, actual))

    predictions = []
    skipped = 0

    for player, games in groups.items():
        games.sort(key=lambda game: (game[0], game[1]))

        dates = [game[0] for game in games]

        if len(dates) != len(set(dates)):
            raise ValueError(
                f"Duplicate game dates for {player}; "
                "exact game order cannot be established"
            )

        history = []

        for game_date, game_id, actual in games:
            if len(history) < min_observations:
                skipped += 1
                history.append(actual)
                continue

            forecast = weighted_average(history, half_life)
            baseline = sum(history) / len(history)

            predictions.append({
                "game_date": game_date,
                "game_id": game_id,
                "player": player,
                "forecast_shots": forecast,
                "baseline_shots": baseline,
                "actual_shots": actual,
                "history_games": len(history),
            })

            history.append(actual)

    if not predictions:
        return {
            "predictions": [],
            "metrics": None,
            "evaluated": 0,
            "skipped": skipped,
            "message": "Not enough historical games to evaluate.",
        }

    count = len(predictions)

    model_absolute_error = 0.0
    model_squared_error = 0.0
    baseline_absolute_error = 0.0
    baseline_squared_error = 0.0

    for item in predictions:
        actual = item["actual_shots"]

        model_error = item["forecast_shots"] - actual
        baseline_error = item["baseline_shots"] - actual

        model_absolute_error += abs(model_error)
        model_squared_error += model_error ** 2

        baseline_absolute_error += abs(baseline_error)
        baseline_squared_error += baseline_error ** 2

    metrics = {
        "weighted_model_mae": model_absolute_error / count,
        "weighted_model_rmse": math.sqrt(
            model_squared_error / count
        ),
        "simple_average_mae": baseline_absolute_error / count,
        "simple_average_rmse": math.sqrt(
            baseline_squared_error / count
        ),
    }

    metrics["mae_improvement"] = (
        metrics["simple_average_mae"]
        - metrics["weighted_model_mae"]
    )

    return {
        "predictions": predictions,
        "metrics": metrics,
        "evaluated": count,
        "skipped": skipped,
        "half_life_games": half_life,
        "message": "Walk-forward shots forecast evaluation complete.",
        "warning": (
            "This tests shot-count forecasting only. "
            "It does not establish betting probabilities, "
            "historical odds or profitability."
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Backtest NHL shots-on-goal forecasts."
    )

    parser.add_argument("csv_file")
    parser.add_argument(
        "--min-observations",
        type=int,
        default=DEFAULT_MIN_OBSERVATIONS,
    )
    parser.add_argument(
        "--half-life",
        type=float,
        default=DEFAULT_HALF_LIFE,
    )

    args = parser.parse_args()

    result = run_backtest(
        load_rows(args.csv_file),
        min_observations=args.min_observations,
        half_life=args.half_life,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
  
