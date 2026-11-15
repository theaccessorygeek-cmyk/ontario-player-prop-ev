
"""Collect historical NHL player game logs from the public NHL Web API.

This collects actual player statistics, not historical sportsbook lines.
No API key or paid data subscription is required.
"""

import argparse
import csv
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


BASE_URL = "https://api-web.nhle.com/v1"
DEFAULT_PLAYER_ID = 8478402

DEFAULT_SEASONS = [
    "20222023",
    "20232024",
    "20242025",
    "20252026",
    "20262027",
]

ROOT = Path(__file__).resolve().parents[1]

FIELDS = [
    "game_date",
    "game_id",
    "player_id",
    "player",
    "team",
    "home_road",
    "shots_on_goal",
    "goals",
    "assists",
    "points",
    "toi",
    "season",
    "game_type",
    "source_url",
    "collected_at_utc",
]


def fetch_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "OntarioPlayerPropEV/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"NHL API returned HTTP {response.status}"
                )

            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"NHL API request failed: HTTP {error.code}"
        ) from error

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Could not connect to NHL API: {error}"
        ) from error


def collect_player_logs(player_id, seasons):
    """Collect regular-season game logs for one NHL player."""

    landing_url = f"{BASE_URL}/player/{player_id}/landing"
    profile = fetch_json(landing_url)

    first_name = profile.get("firstName", {}).get("default", "")
    last_name = profile.get("lastName", {}).get("default", "")
    player_name = f"{first_name} {last_name}".strip()

    if not player_name:
        raise RuntimeError("NHL API did not return a player name")

    collected_at = datetime.now(timezone.utc).isoformat()
    results = []

    for season in seasons:
        if (
            len(season) != 8
            or not season.isdigit()
            or int(season[4:]) != int(season[:4]) + 1
        ):
            raise ValueError(
                f"Invalid NHL season format: {season}"
            )

        url = (
            f"{BASE_URL}/player/{player_id}"
            f"/game-log/{season}/2"
        )

        print(f"Collecting {player_name}: {season}")

        payload = fetch_json(url)
        games = payload.get("gameLog")

        if not isinstance(games, list):
            raise RuntimeError(
                f"Unexpected game-log response for season {season}"
            )

        for game in games:
            game_date = game.get("gameDate")
            game_id = game.get("gameId")
            shots = game.get("shots")

            if not game_date or game_id is None or shots is None:
                print(
                    f"Skipping incomplete game record in {season}",
                    file=sys.stderr,
                )
                continue

            try:
                shots = int(shots)
                datetime.strptime(game_date, "%Y-%m-%d")
            except (TypeError, ValueError):
                print(
                    f"Skipping invalid game record in {season}",
                    file=sys.stderr,
                )
                continue

            if shots < 0:
                continue

            results.append({
                "game_date": game_date,
                "game_id": game_id,
                "player_id": player_id,
                "player": player_name,
                "team": game.get("teamAbbrev", ""),
                "home_road": game.get("homeRoadFlag", ""),
                "shots_on_goal": shots,
                "goals": game.get("goals", ""),
                "assists": game.get("assists", ""),
                "points": game.get("points", ""),
                "toi": game.get("toi", ""),
                "season": season,
                "game_type": "regular",
                "source_url": url,
                "collected_at_utc": collected_at,
            })

    results.sort(
        key=lambda row: (row["game_date"], row["game_id"])
    )

    return results


def save_csv(rows, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FIELDS,
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Collect historical NHL player game logs."
    )

    parser.add_argument(
        "--player-id",
        type=int,
        default=DEFAULT_PLAYER_ID,
    )

    parser.add_argument(
        "--seasons",
        nargs="+",
        default=DEFAULT_SEASONS,
    )

    parser.add_argument(
        "--output",
        default="data/nhl_player_game_logs.csv",
    )

    args = parser.parse_args()

    rows = collect_player_logs(
        args.player_id,
        args.seasons,
    )

    output_path = ROOT / args.output
    save_csv(rows, output_path)

    print()
    print(f"Player games collected: {len(rows)}")
    print(f"Output saved to: {output_path}")


if __name__ == "__main__":
    main()
  
