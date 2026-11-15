import unittest
from datetime import datetime, timedelta, timezone

from src.backtest import run_backtest


class TestWalkForwardBacktest(unittest.TestCase):

    def setUp(self):
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)

        self.rows = [
            {
                "game_datetime": (
                    start + timedelta(days=i)
                ).isoformat(),
                "player": "Test Player",
                "market": "shots",
                "line": "2.5",
                "actual": str(2 + (i % 3)),
            }
            for i in range(21)
        ]

    def test_uses_only_prior_games(self):
        result = run_backtest(self.rows)

        self.assertEqual(result["evaluated"], 1)
        self.assertEqual(result["skipped"], 20)
        self.assertEqual(
            result["predictions"][0]["history_games"], 20
        )

    def test_future_result_does_not_change_prediction(self):
        first = run_backtest(self.rows)

        changed = [row.copy() for row in self.rows]
        changed[-1]["actual"] = "100"

        second = run_backtest(changed)

        self.assertEqual(
            first["predictions"][0]["probabilities"],
            second["predictions"][0]["probabilities"],
        )

    def test_insufficient_history_returns_no_metrics(self):
        result = run_backtest(self.rows[:10])

        self.assertEqual(result["evaluated"], 0)
        self.assertIsNone(result["metrics"])

    def test_metrics_are_in_valid_ranges(self):
        result = run_backtest(self.rows)

        self.assertIsNotNone(result["metrics"])
        self.assertGreaterEqual(result["metrics"]["brier_score"], 0)
        self.assertGreaterEqual(result["metrics"]["log_loss"], 0)
        self.assertGreaterEqual(result["metrics"]["accuracy"], 0)
        self.assertLessEqual(result["metrics"]["accuracy"], 1)

    def test_timezone_is_required(self):
        rows = [row.copy() for row in self.rows]
        rows[0]["game_datetime"] = "2025-01-01T12:00:00"

        with self.assertRaises(ValueError):
            run_backtest(rows)

    def test_same_day_games_are_ordered_by_time(self):
        rows = [row.copy() for row in self.rows]
        rows[0]["game_datetime"] = "2025-01-01T10:00:00+00:00"
        rows[1]["game_datetime"] = "2025-01-01T11:00:00+00:00"

        result = run_backtest(rows)

        self.assertEqual(result["evaluated"], 1)


if __name__ == "__main__":
    unittest.main()
