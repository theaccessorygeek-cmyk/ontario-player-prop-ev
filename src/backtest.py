"""Chronological walk-forward backtesting for player props."""

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone

from src.projections import estimate_probabilities


CLASSES = ("over", "under", "push")
EPSILON = 1e-15


def parse_game_datetime(value):
    """Parse an ISO 8601 timestamp and normalize it to UTC."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise ValueError("game_datetime must be a valid ISO 8601 timestamp")

    if parsed.tzinfo is None:
        raise ValueError("game_datetime must include a timezone")

    return parsed.astimezone(timezone.utc)


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def run_backtest(rows, min_observations=20):
    if not isinstance(rows, list):
        raise ValueError("Rows must be a list")

    if isinstance(min_observations, bool) or not isinstance(min_observations, int) or min_observations < 1:
        raise ValueError("min_observations must be a positive integer")

    groups = defaultdict(list)

    for row in rows:
        try:
            game_datetime = parse_game_datetime(row["game_datetime"])
            player = str(row["player"]).strip()
            market = str(row["market"]).strip()
            line = float(row["line"])
            actual = float(row["actual"])
        except (KeyError, TypeError, ValueError):
            raise ValueError(
                "Each row needs valid game_datetime, player, market, line and actual fields"
            )

        if not player or not market:
            raise ValueError("Player and market cannot be blank")

        if not math.isfinite(line) or not math.isfinite(actual):
            raise ValueError("Line and actual must be finite numbers")

        groups[(player, market)].append(
            (game_datetime, line, actual)
        )

    predictions = []
    skipped = 0

    for key, games in groups.items():
        games.sort(key=lambda item: item[0])

        timestamps = [game[0] for game in games]
        if len(timestamps) != len(set(timestamps)):
            raise ValueError(
                f"Duplicate game timestamps for {key[0]} / {key[1]}"
            )

        history = []

        for game_datetime, line, actual in games:
            if len(history) < min_observations:
                skipped += 1
                history.append(actual)
                continue

            estimate = estimate_probabilities(
                history,
                line,
                min_observations=min_observations,
            )

            if actual > line:
                outcome = "over"
            elif actual < line:
                outcome = "under"
            else:
                outcome = "push"

            predictions.append({
                "game_datetime": game_datetime.isoformat(),
                "player": key[0],
                "market": key[1],
                "line": line,
                "actual": actual,
                "outcome": outcome,
                "probabilities": {
                    "over": estimate["model_over_probability"],
                    "under": estimate["model_under_probability"],
                    "push": estimate["model_push_probability"],
                },
                "history_games": len(history),
                "effective_sample_size": estimate["effective_sample_size"],
            })

            history.append(actual)

    if not predictions:
        return {
            "predictions": [],
            "metrics": None,
            "evaluated": 0,
            "skipped": skipped,
            "message": "Not enough historical data to evaluate predictions.",
        }

    brier_total = 0.0
    log_loss_total = 0.0
    correct = 0

    for prediction in predictions:
        probabilities = prediction["probabilities"]
        actual_class = prediction["outcome"]

        brier_total += sum(
            (probabilities[name] - (1.0 if name == actual_class else 0.0)) ** 2
            for name in CLASSES
        )

        log_loss_total -= math.log(
            max(probabilities[actual_class], EPSILON)
        )

        predicted_class = max(
            CLASSES, key=lambda name: probabilities[name]
        )

        if predicted_class == actual_class:
            correct += 1

    count = len(predictions)

    return {
        "predictions": predictions,
        "metrics": {
            "brier_score": brier_total / count,
            "log_loss": log_loss_total / count,
            "accuracy": correct / count,
        },
        "evaluated": count,
        "skipped": skipped,
        "message": "Walk-forward evaluation complete.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    args = parser.parse_args()

    result = run_backtest(load_rows(args.csv_file))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
