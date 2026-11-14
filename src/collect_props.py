
"""Collect recent player-prop reference prices from ParlayAPI.

This is a data collector, not an Ontario sportsbook verifier.
It never converts provider rows into approved bets.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://parlay-api.com/v1"

SPORTS_TO_CHECK = [
    "icehockey_nhl",
    "basketball_nba",
    "americanfootball_nfl",
    "baseball_mlb",
    "soccer_epl",
    "tennis_atp",
    "tennis_wta",
    "americanfootball_ncaaf",
    "basketball_ncaab",
]

ROOT = Path(__file__).resolve().parents[1]


def api_get(path, params=None):
    api_key = os.environ.get("PARLAY_API_KEY")

    if not api_key:
        raise RuntimeError("PARLAY_API_KEY secret is missing")

    url = BASE_URL + path

    if params:
        url += "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        url,
        headers={
            "X-API-Key": api_key,
            "Accept": "application/json",
            "User-Agent": "OntarioPlayerPropEV/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            body = response.read().decode("utf-8")

            return {
                "status": response.status,
                "headers": dict(response.headers.items()),
                "body": json.loads(body) if body else None,
            }

    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")

        if error.code in (401, 403):
            raise RuntimeError(
                f"API authentication or plan error ({error.code}). "
                "Check the key and account plan."
            )

        return {
            "status": error.code,
            "headers": dict(error.headers.items()),
            "body": {"error": detail},
        }


def main():
    output_dir = ROOT / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Checking active sports...")
    sports_response = api_get("/sports")

    if sports_response["status"] != 200:
        raise RuntimeError(
            f"Could not retrieve active sports: "
            f"HTTP {sports_response['status']}"
        )

    active_sports = {
        item.get("key")
        for item in (sports_response["body"] or [])
        if isinstance(item, dict)
    }

    snapshot = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "provider": "ParlayAPI",
        "purpose": "Reference prices only; not Ontario verification",
        "sports_checked": [],
        "results": [],
    }

    for sport in SPORTS_TO_CHECK:
        if sport not in active_sports:
            print(f"Skipping inactive sport: {sport}")
            snapshot["sports_checked"].append({
                "sport": sport,
                "status": "inactive_or_not_listed",
            })
            continue

        print(f"Collecting props: {sport}")

        result = api_get(
            f"/sports/{sport}/props",
            {
                "maxAgeSec": 900,
                "limit": 10000,
            },
        )

        headers = {
            key.lower(): value
            for key, value in result["headers"].items()
        }

        body = result["body"]
        rows = body if isinstance(body, list) else []

        entry = {
            "sport": sport,
            "http_status": result["status"],
            "row_count": len(rows),
            "has_more": headers.get("x-result-has-more"),
            "truncated": headers.get("x-result-truncated"),
            "truncated_hint": headers.get("x-result-truncated-hint"),
            "degraded_sources": headers.get("x-result-degraded"),
            "credits_remaining": headers.get("x-requests-remaining"),
            "rows": rows,
        }

        snapshot["sports_checked"].append({
            "sport": sport,
            "status": result["status"],
            "row_count": len(rows),
            "truncated": headers.get("x-result-truncated"),
            "degraded_sources": headers.get("x-result-degraded"),
        })

        if result["status"] == 200:
            snapshot["results"].append(entry)
            print(f"  Received {len(rows)} rows")
        else:
            snapshot["results"].append({
                "sport": sport,
                "http_status": result["status"],
                "error": body,
                "rows": [],
            })
            print(f"  Provider returned HTTP {result['status']}")

    destination = output_dir / "props_snapshot.json"

    destination.write_text(
        json.dumps(snapshot, indent=2),
        encoding="utf-8",
    )

    total_rows = sum(
        item.get("row_count", 0)
        for item in snapshot["results"]
    )

    print(f"Total reference rows collected: {total_rows}")
    print(f"Saved: {destination}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"COLLECTOR FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
      
