
import unittest

from src.nhl_sog_backtest import (
    run_backtest,
    weighted_average,
)


class TestNHLSOGBacktest(unittest.TestCase):

    def setUp(self):
        self.rows = [
            {
                "game_date": f"2025-01-{i:02d}",
                "game_id": str(i),
                "player": "Connor McDavid",
                "shots_on_goal": str(2 + (i % 3)),
            }
            for i in range(1, 26)
        ]

    def test_weighted_average(self):
        result = weighted_average([1, 3, 5], 10)

        self.assertGreater(result, 3)
        self.assertLess(result, 5)

    def test_walk_forward_uses_prior_games(self):
        result = run_backtest(self.rows)

        self.assertEqual(result["evaluated"], 5)
        self.assertEqual(result["skipped"], 20)
        self.assertEqual(
            result["predictions"][0]["history_games"], 20
        )

    def test_future_result_does_not_change_first_forecast(self):
        first = run_backtest(self.rows)

        changed = [row.copy() for row in self.rows]
        changed[-1]["shots_on_goal"] = "100"

        second = run_backtest(changed)

        self.assertEqual(
            first["predictions"][0]["forecast_shots"],
            second["predictions"][0]["forecast_shots"],
        )

    def test_insufficient_history(self):
        result = run_backtest(self.rows[:10])

        self.assertEqual(result["evaluated"], 0)
        self.assertIsNone(result["metrics"])

    def test_metrics_are_nonnegative(self):
        result = run_backtest(self.rows)

        self.assertGreaterEqual(
            result["metrics"]["weighted_model_mae"], 0
        )
        self.assertGreaterEqual(
            result["metrics"]["weighted_model_rmse"], 0
        )

    def test_duplicate_dates_rejected(self):
        rows = [row.copy() for row in self.rows]
        rows[1]["game_date"] = rows[0]["game_date"]

        with self.assertRaises(ValueError):
            run_backtest(rows)

    def test_negative_shots_rejected(self):
        rows = [row.copy() for row in self.rows]
        rows[0]["shots_on_goal"] = "-1"

        with self.assertRaises(ValueError):
            run_backtest(rows)

    def test_invalid_half_life_rejected(self):
        with self.assertRaises(ValueError):
            run_backtest(self.rows, half_life=0)


if __name__ == "__main__":
    unittest.main()
  
