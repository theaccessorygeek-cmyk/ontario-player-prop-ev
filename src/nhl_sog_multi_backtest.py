"""Compare walk-forward NHL SOG forecasts across multiple players.

Input is a combined CSV in the schema produced by src.nhl_game_logs.
This evaluates forecast accuracy only; it does not estimate betting ROI.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from src.nhl_sog_backtest import (
    DEFAULT_HALF_LIFE,
    DEFAULT_MIN_OBSERVATIONS,
    run_backtest,
)


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else [
        "player", "game_date", "game_id", "history_games",
        "forecast_shots", "baseline_shots", "actual_shots",
        "model_absolute_error", "baseline_absolute_error",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_multi_backtest(
    rows,
    min_observations=DEFAULT_MIN_OBSERVATIONS,
    half_life=DEFAULT_HALF_LIFE,
):
    grouped = defaultdict(list)
    for row in rows:
        player = str(row.get("player", "")).strip()
        if not player:
            raise ValueError("Every row must contain a player name")
        grouped[player].append(row)

    summaries = []
    predictions = []
    skipped_total = 0

    for player in sorted(grouped):
        result = run_backtest(
            grouped[player],
            min_observations=min_observations,
            half_life=half_life,
        )
        skipped_total += result["skipped"]
        if result["metrics"] is None:
            summaries.append({
                "player": player,
                "games": len(grouped[player]),
                "evaluated": 0,
                "skipped": result["skipped"],
                "weighted_model_mae": None,
                "weighted_model_rmse": None,
                "simple_average_mae": None,
                "simple_average_rmse": None,
                "mae_improvement_pct": None,
            })
            continue

        metrics = result["metrics"]
        baseline_mae = metrics["simple_average_mae"]
        improvement_pct = (
            100 * metrics["mae_improvement"] / baseline_mae
            if baseline_mae else 0.0
        )
        summaries.append({
            "player": player,
            "games": len(grouped[player]),
            "evaluated": result["evaluated"],
            "skipped": result["skipped"],
            "weighted_model_mae": metrics["weighted_model_mae"],
            "weighted_model_rmse": metrics["weighted_model_rmse"],
            "simple_average_mae": baseline_mae,
            "simple_average_rmse": metrics["simple_average_rmse"],
            "mae_improvement_pct": improvement_pct,
        })
        for item in result["predictions"]:
            actual = item["actual_shots"]
            predictions.append({
                "player": player,
                "game_date": item["game_date"],
                "game_id": item["game_id"],
                "history_games": item["history_games"],
                "forecast_shots": item["forecast_shots"],
                "baseline_shots": item["baseline_shots"],
                "actual_shots": actual,
                "model_absolute_error": abs(item["forecast_shots"] - actual),
                "baseline_absolute_error": abs(item["baseline_shots"] - actual),
            })

    evaluated = len(predictions)
    if evaluated:
        weighted_mae = sum(p["model_absolute_error"] for p in predictions) / evaluated
        baseline_mae = sum(p["baseline_absolute_error"] for p in predictions) / evaluated
        overall = {
            "evaluated": evaluated,
            "weighted_model_mae": weighted_mae,
            "simple_average_mae": baseline_mae,
            "mae_improvement_pct": (
                100 * (baseline_mae - weighted_mae) / baseline_mae
                if baseline_mae else 0.0
            ),
        }
    else:
        overall = None

    return {
        "summaries": summaries,
        "predictions": predictions,
        "overall": overall,
        "skipped": skipped_total,
        "min_observations": min_observations,
        "half_life": half_life,
    }


def write_report(path, result):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NHL Shots-on-Goal Multi-Player Backtest",
        "",
        f"- Minimum prior games: {result['min_observations']}",
        f"- EWMA half-life: {result['half_life']} games",
        "- Validation: chronological walk-forward, player-by-player",
        "- Benchmark: simple average of all prior games",
        "- Data: regular-season player game logs from the public NHL API",
        "- Interpretation: forecasting accuracy only; no sportsbook odds, EV, or ROI",
        "",
        "## Player results",
        "",
        "| Player | Games | Evaluated | EWMA MAE | Baseline MAE | MAE improvement |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for item in result["summaries"]:
        if item["evaluated"]:
            lines.append(
                f"| {item['player']} | {item['games']} | {item['evaluated']} | "
                f"{item['weighted_model_mae']:.3f} | "
                f"{item['simple_average_mae']:.3f} | "
                f"{item['mae_improvement_pct']:+.2f}% |"
            )
        else:
            lines.append(
                f"| {item['player']} | {item['games']} | 0 | — | — | — |"
            )
    lines.extend(["", "## Overall results", ""])
    if result["overall"]:
        overall = result["overall"]
        lines.extend([
            f"- Evaluated predictions: {overall['evaluated']}",
            f"- EWMA MAE: {overall['weighted_model_mae']:.3f}",
            f"- Baseline MAE: {overall['simple_average_mae']:.3f}",
            f"- MAE improvement: {overall['mae_improvement_pct']:+.2f}%",
        ])
    else:
        lines.append("No player had enough historical games to produce a forecast.")
    lines.extend([
        "",
        "## Method and limitations",
        "",
        "Each forecast is generated before the target game using only that player's earlier games. "
        "The first forecast is made only after the configured minimum history is reached. "
        "The 10-game half-life weights recent observations more heavily. The baseline uses "
        "the unweighted mean of all prior games.",
        "",
        "This test does not use historical sportsbook lines or prices and must not be interpreted "
        "as evidence of positive expected value or profitability. Results are player-level "
        "descriptive evidence; the sample is not a randomized or independent experiment.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file")
    parser.add_argument("--min-observations", type=int, default=DEFAULT_MIN_OBSERVATIONS)
    parser.add_argument("--half-life", type=float, default=DEFAULT_HALF_LIFE)
    parser.add_argument("--output-dir", default="reports/nhl_sog")
    args = parser.parse_args()

    result = run_multi_backtest(
        load_rows(args.csv_file),
        min_observations=args.min_observations,
        half_life=args.half_life,
    )
    output_dir = Path(args.output_dir)
    write_csv(output_dir / "nhl_sog_predictions.csv", result["predictions"])
    write_csv(output_dir / "nhl_sog_player_summary.csv", result["summaries"])
    write_report(output_dir / "nhl_sog_multi_player_report.md", result)

    print(f"Players tested: {len(result['summaries'])}")
    print(f"Predictions evaluated: {len(result['predictions'])}")
    if result["overall"]:
        print(f"EWMA MAE: {result['overall']['weighted_model_mae']:.3f}")
        print(f"Baseline MAE: {result['overall']['simple_average_mae']:.3f}")
        print(f"MAE improvement: {result['overall']['mae_improvement_pct']:+.2f}%")
    print(f"Reports saved to: {output_dir}")


if __name__ == "__main__":
    main()
