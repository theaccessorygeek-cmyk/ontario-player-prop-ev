
"""One budget-capped rotating ParlayAPI query per scheduled day."""
import json
import os
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "reports" / "props_snapshot.json"
REPORT = ROOT / "reports" / "targeted_collection.md"
BASE = "https://parlay-api.com/v1"
RESERVE = 100
COST = 3

SPORTS = [
    "icehockey_nhl", "basketball_nba", "americanfootball_nfl",
    "baseball_mlb", "soccer_epl", "tennis_atp", "tennis_wta",
    "americanfootball_ncaaf", "basketball_ncaab",
]
BOOKS = [
    "fanduel", "draftkings", "bet365", "betmgm",
    "caesars", "betrivers_ca", "hardrock",
]


def main():
    if os.environ.get("GITHUB_EVENT_NAME") != "schedule":
        print("Manual run: targeted request skipped to protect credits.")
        return

    if not SNAPSHOT.exists():
        raise SystemExit("Baseline snapshot is missing.")

    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    remaining = []

    for item in snapshot.get("results", []):
        try:
            remaining.append(int(item["credits_remaining"]))
        except (KeyError, TypeError, ValueError):
            pass

    if not remaining:
        reason = "Skipped: no readable API credits-remaining value."
        snapshot["targeted_collection"] = {"status": "skipped", "reason": reason}
        REPORT.write_text("# Targeted collection\n\n" + reason + "\n")
        SNAPSHOT.write_text(json.dumps(snapshot, indent=2))
        print(reason)
        return

    credits = min(remaining)
    if credits < RESERVE + COST:
        reason = f"Skipped: {credits} credits remain; protecting {RESERVE}."
        snapshot["targeted_collection"] = {"status": "skipped", "reason": reason}
        REPORT.write_text("# Targeted collection\n\n" + reason + "\n")
        SNAPSHOT.write_text(json.dumps(snapshot, indent=2))
        print(reason)
        return

    now = datetime.now(timezone.utc)
    slot = (now.timetuple().tm_yday - 1) % (len(SPORTS) * len(BOOKS))
    sport = SPORTS[slot % len(SPORTS)]
    book = BOOKS[(slot // len(SPORTS)) % len(BOOKS)]

    key = os.environ.get("PARLAY_API_KEY")
    if not key:
        raise SystemExit("PARLAY_API_KEY secret is missing.")

    query = urllib.parse.urlencode({
        "bookmakers": book, "maxAgeSec": 900, "limit": 10000
    })
    url = f"{BASE}/sports/{sport}/props?{query}"
    request = urllib.request.Request(
        url, headers={"X-API-Key": key, "Accept": "application/json"}
    )

    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            status = response.status
            headers = {k.lower(): v for k, v in response.headers.items()}
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        status = error.code
        headers = {k.lower(): v for k, v in error.headers.items()}
        body = {"error": error.read().decode("utf-8", errors="replace")}

    rows = body if isinstance(body, list) else []
    result = {
        "sport": sport,
        "bookmaker_filter": book,
        "http_status": status,
        "row_count": len(rows),
        "has_more": headers.get("x-result-has-more"),
        "truncated": headers.get("x-result-truncated"),
        "truncated_hint": headers.get("x-result-truncated-hint"),
        "credits_remaining_after": headers.get("x-requests-remaining"),
        "rows": rows,
        "purpose": "Reference data only; Ontario availability unverified",
    }

    snapshot["targeted_collection"] = {
        "status": "completed" if status == 200 else "http_error",
        "requested_at": now.isoformat(),
        "credits_before": credits,
        "estimated_cost": COST,
        "reserve": RESERVE,
        "result": result,
    }

    REPORT.write_text(
        "# Targeted collection\n\n"
        f"- Sport: {sport}\n- Book filter: {book}\n"
        f"- HTTP status: {status}\n- Rows: {len(rows)}\n"
        f"- Has more: {result['has_more']}\n"
        f"- Truncated: {result['truncated']}\n"
        f"- Credits before: {credits}\n- Reserve: {RESERVE}\n\n"
        "Reference data only. This does not prove Ontario availability "
        "or that any quote is tradable. Truncated data is incomplete.\n"
    )
    SNAPSHOT.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"Targeted query: {sport} / {book}; HTTP {status}; rows {len(rows)}")
    print(f"Has more: {result['has_more']}; truncated: {result['truncated']}")


if __name__ == "__main__":
    main()
  
