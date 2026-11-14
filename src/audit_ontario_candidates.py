
"""Audit potential Ontario-operator player-prop quotes.

Being listed as an Ontario operator does not prove that a particular
provider quote is sourced from Ontario or available to an Ontario account.
This script is a conservative data-quality audit, not bet approval.
"""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports" / "props_snapshot.json"
OUTPUT = ROOT / "reports" / "ontario_candidate_audit.md"

# Operator brands listed for sports betting by iGaming Ontario.
# Provider slugs are mapped cautiously; quote jurisdiction remains unverified.
ONTARIO_SOURCES = {
    "fanduel": "FanDuel",
    "draftkings": "DraftKings",
    "bet365": "Bet365",
    "betmgm": "BetMGM",
    "caesars": "Caesars",
    "betrivers_ca": "BetRivers (CA-labelled feed)",
    "hardrock": "Hard Rock Bet",
}

MAX_AGE_SECONDS = 900


def valid_price(value):
    if value is None or isinstance(value, bool):
        return False
    try:
        return float(value) != 0
    except (TypeError, ValueError):
        return False


def is_adjusted_or_dfs(row):
    return (
        row.get("is_dfs_flat_payout") is True
        or row.get("dfs_normalized") is True
        or str(row.get("odds_type", "")).lower() in ("goblin", "demon")
        or str(row.get("projection_type", "")).upper()
        in ("GOBLIN", "DEMON")
    )


def is_player_prop(row):
    market_key = str(row.get("market_key", "")).lower()
    market = str(row.get("market", "")).lower()
    player = str(row.get("player", "")).strip()

    if not player or not market_key.startswith("player_"):
        return False

    excluded = (
        "anytime",
        "first scorer",
        "first goal",
        "to score",
        "goalscorer",
    )
    if any(term in market for term in excluded):
        return False

    return True


def is_fresh(row):
    age = row.get("age_seconds")
    return (
        isinstance(age, (int, float))
        and 0 <= age <= MAX_AGE_SECONDS
    )


def main():
    if not SOURCE.exists():
        raise SystemExit("Snapshot not found. Run the collector first.")

    with SOURCE.open(encoding="utf-8") as file:
        snapshot = json.load(file)

    totals = Counter()
    samples = []
    matched_keys = set()

    for result in snapshot.get("results", []):
        for row in result.get("rows", []):
            if not isinstance(row, dict):
                continue

            book = str(row.get("bookmaker", "")).lower()

            if book not in ONTARIO_SOURCES:
                continue

            totals[(book, "all")] += 1

            if is_adjusted_or_dfs(row):
                continue

            if not (
                valid_price(row.get("over_price"))
                and valid_price(row.get("under_price"))
            ):
                continue

            totals[(book, "two_sided")] += 1

            if not is_player_prop(row):
                continue

            totals[(book, "player_prop")] += 1

            if not is_fresh(row):
                continue

            totals[(book, "fresh")] += 1

            if row.get("line") is None:
                continue

            if not row.get("event_id") or not row.get("period"):
                continue

            totals[(book, "complete")] += 1

            key = (
                book,
                row.get("sport_key"),
                row.get("canonical_event_id") or row.get("event_id"),
                str(row.get("player", "")).strip().casefold(),
                row.get("market_key"),
                row.get("period"),
                row.get("line"),
            )

            matched_keys.add(key)

            if len(samples) < 100:
                samples.append({
                    "book": ONTARIO_SOURCES[book],
                    "sport": row.get("sport_key"),
                    "event": (
                        f"{row.get('away_team', '')} at "
                        f"{row.get('home_team', '')}"
                    ),
                    "player": row.get("player"),
                    "market": row.get("market"),
                    "line": row.get("line"),
                    "over": row.get("over_price"),
                    "under": row.get("under_price"),
                    "age_seconds": row.get("age_seconds"),
                })

    lines = [
        "# Ontario Operator Candidate Audit",
        "",
        f"Snapshot: {snapshot.get('collected_at')}",
        "",
        "**Important:** Operator listing is not proof that a quote is "
        "Ontario-sourced or available to an Ontario account.",
        "",
        "No bets are approved by this audit.",
        "",
        "## Counts by provider label",
        "",
        "| Provider | All rows | Two-sided non-DFS | Player props | Fresh | Complete |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for book, display in ONTARIO_SOURCES.items():
        values = [
            totals[(book, stage)]
            for stage in ("all", "two_sided", "player_prop", "fresh", "complete")
        ]
        lines.append(
            f"| {display} | " + " | ".join(map(str, values)) + " |"
        )

    lines += [
        "",
        f"## Unique complete candidate keys: {len(matched_keys)}",
        "",
        "These keys are grouped by provider, sport, event, player, "
        "market, period and line.",
        "",
        "## Sample records",
        "",
        "| Provider | Sport | Player | Market | Line | Over | Under | Age (sec) |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]

    for item in samples:
        lines.append(
            f"| {item['book']} | {item['sport']} | {item['player']} "
            f"| {item['market']} | {item['line']} | {item['over']} "
            f"| {item['under']} | {item['age_seconds']} |"
        )

    lines += [
        "",
        "## Restrictions",
        "",
        "- Provider labels do not establish Ontario quote jurisdiction.",
        "- No player identity, lineup, injury or market settlement is verified here.",
        "- A two-sided quote is not automatically a valid player prop.",
        "- No-vig probabilities and expected value are not calculated here.",
        "- Collection truncation means this snapshot may not contain every market.",
        "- All candidates require further source and event verification.",
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("Ontario candidate audit completed.")
    for book, display in ONTARIO_SOURCES.items():
        print(
            display,
            "all:", totals[(book, "all")],
            "two-sided:", totals[(book, "two_sided")],
            "player props:", totals[(book, "player_prop")],
            "fresh:", totals[(book, "fresh")],
            "complete:", totals[(book, "complete")],
        )

    print("Unique complete candidate keys:", len(matched_keys))
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
  
