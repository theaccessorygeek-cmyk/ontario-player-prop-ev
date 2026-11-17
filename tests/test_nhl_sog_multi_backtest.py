import unittest

from src.nhl_sog_multi_backtest import run_multi_backtest


class TestNHLSOGMultiBacktest(unittest.TestCase):
    def setUp(self):
        self.rows = []
        for player in ("Connor McDavid", "Leon Draisaitl"):
            for day in range(1, 26):
                self.rows.append({
                    "game_date": f"2025-01-{day:02d}",
                    "game_id": f"{player}-{day}",
                    "player": player,
                    "shots_on_goal": str(2 + (day % 3)),
                })

    def test_runs_separate_walk_forward_tests(self):
        result = run_multi_backtest(self.rows)
        self.assertEqual(len(result["summaries"]), 2)
        self.assertEqual(len(result["predictions"]), 10)
        self.assertTrue(all(x["evaluated"] == 5 for x in result["summaries"]))
        self.assertEqual(result["overall"]["evaluated"], 10)

    def test_each_player_starts_with_20_game_history(self):
        result = run_multi_backtest(self.rows)
        for player in ("Connor McDavid", "Leon Draisaitl"):
            player_predictions = [
                x for x in result["predictions"] if x["player"] == player
            ]
            self.assertEqual(player_predictions[0]["history_games"], 20)
            self.assertEqual(player_predictions[-1]["history_games"], 24)

    def test_insufficient_player_history_is_reported(self):
        result = run_multi_backtest(self.rows[:10])
        self.assertIsNone(result["overall"])
        self.assertEqual(result["summaries"][0]["evaluated"], 0)

    def test_blank_player_rejected(self):
        rows = [self.rows[0].copy()]
        rows[0]["player"] = " "
        with self.assertRaises(ValueError):
            run_multi_backtest(rows)


if __name__ == "__main__":
    unittest.main()
