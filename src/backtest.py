"""Chronological walk-forward backtesting for player props."""

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import date

from src.projections import estimate_probabilities


CLASSES = ("over", "under", "push")
EPSILON = 1e-15


def load_rows(path):
    """Load historical player results from a CSV file."""
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def run_backtest(rows, min_observations=20):
    """Evaluate predictions using only earlier games for each player/market."""

    if not isinstance(rows, list):
        raise ValueError("Rows must be a list")

    groups = defaultdict(list)

    for row in rows:
        try:
            game_date = date.fromisoformat(row["date"])
            player = str(row["player"]).strip()
            market = str(row["market"]).strip()
            line = float(row["line"])
            actual = float(row["actual"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("Each row needs valid date, player, market, line and actual fields")

        if not player or not market:
            raise ValueError("Player and market cannot be blank")

        if not math.isfinite(line) or not math.isfinite(actual):
            raise ValueError("Line and actual must be finite numbers")

        groups[(player, market)].append(
            (game_date, line, actual)
        )

    predictions = []
    skipped = 0

    for key, games in groups.items():
        games.sort(key=lambda item: item[0])

        dates = [game[0] for game in games]
        if len(dates) != len(set(dates)):
            raise ValueError(
                f"Duplicate dates found for {key[0]} / {key[1]}"
            )

        history = []

        for game_date, line, actual in games:
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
                "date": game_date.isoformat(),
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

            # Add this game's result only after making its prediction.
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
    parser.add_argument(
        "csv_file",
        help="CSV file with date,player,market,line,actual columns",
    )
    args = parser.parse_args()

    result = run_backtest(load_rows(args.csv_file))

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
