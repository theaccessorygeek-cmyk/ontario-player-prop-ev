import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.nhl_game_logs import (
    collect_player_logs,
    save_csv,
)


class TestNHLGameLogs(unittest.TestCase):

    def setUp(self):
        self.profile = {
            "firstName": {"default": "Connor"},
            "lastName": {"default": "McDavid"},
        }

        self.game_log = {
            "gameLog": [
                {
                    "gameDate": "2025-01-10",
                    "gameId": 2024020002,
                    "shots": 4,
                    "goals": 1,
                    "assists": 2,
                    "points": 3,
                    "toi": "21:30",
                    "teamAbbrev": "EDM",
                    "homeRoadFlag": "H",
                },
                {
                    "gameDate": "2025-01-08",
                    "gameId": 2024020001,
                    "shots": 2,
                    "goals": 0,
                    "assists": 1,
                    "points": 1,
                    "toi": "20:10",
                    "teamAbbrev": "EDM",
                    "homeRoadFlag": "R",
                },
            ]
        }

    @patch("src.nhl_game_logs.fetch_json")
    def test_collects_and_sorts_games(self, mock_fetch):
        mock_fetch.side_effect = [
            self.profile,
            self.game_log,
        ]

        rows = collect_player_logs(
            8478402,
            ["20242025"],
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(
            rows[0]["game_date"], "2025-01-08"
        )
        self.assertEqual(
            rows[1]["game_date"], "2025-01-10"
        )
        self.assertEqual(
            rows[0]["player"], "Connor McDavid"
        )
        self.assertEqual(
            rows[1]["shots_on_goal"], 4
        )

    @patch("src.nhl_game_logs.fetch_json")
    def test_invalid_season_rejected(self, mock_fetch):
        mock_fetch.return_value = self.profile

        with self.assertRaises(ValueError):
            collect_player_logs(
                8478402,
                ["20242026"],
            )

    @patch("src.nhl_game_logs.fetch_json")
    def test_unexpected_game_log_rejected(self, mock_fetch):
        mock_fetch.side_effect = [
            self.profile,
            {},
        ]

        with self.assertRaises(RuntimeError):
            collect_player_logs(
                8478402,
                ["20242025"],
            )

    @patch("src.nhl_game_logs.fetch_json")
    def test_incomplete_games_are_skipped(self, mock_fetch):
        mock_fetch.side_effect = [
            self.profile,
            {
                "gameLog": [
                    {
                        "gameDate": "2025-01-10",
                        "gameId": 123,
                        "shots": 3,
                    },
                    {
                        "gameDate": "2025-01-11",
                        "gameId": 124,
                    },
                ]
            },
        ]

        rows = collect_player_logs(
            8478402,
            ["20242025"],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["shots_on_goal"], 3
        )

    def test_saves_csv_file(self):
        rows = [{
            "game_date": "2025-01-10",
            "game_id": 123,
            "player_id": 8478402,
            "player": "Connor McDavid",
            "team": "EDM",
            "home_road": "H",
            "shots_on_goal": 4,
            "goals": 1,
            "assists": 2,
            "points": 3,
            "toi": "21:30",
            "season": "20242025",
            "game_type": "regular",
            "source_url": "https://example.com",
            "collected_at_utc": "2025-01-11T00:00:00+00:00",
        }]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "logs.csv"

            save_csv(rows, path)

            with path.open(
                newline="",
                encoding="utf-8",
            ) as file:
                saved = list(csv.DictReader(file))

        self.assertEqual(len(saved), 1)
        self.assertEqual(
            saved[0]["shots_on_goal"], "4"
        )


if __name__ == "__main__":
    unittest.main()
