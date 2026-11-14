
"""Conservative classification of collected prop prices."""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports" / "props_snapshot.json"
OUTPUT = ROOT / "reports" / "classification.md"

SPORTSBOOKS = {
    "fanduel", "draftkings", "betrivers", "betrivers_ca",
    "bet365", "betmgm", "caesars", "fanatics",
    "bovada", "hardrock", "parx", "fliff",
}

DFS_BOOKS = {
    "prizepicks", "underdog", "betr", "sleeper", "pick6"
}

EXCHANGES = {"novig", "kalshi", "polymarket"}

SINGLE_OUTCOME_TERMS = (
    "anytime goal",
    "anytime td",
    "anytime touchdown",
    "first goal",
    "first scorer",
    "first touchdown",
    "first td",
    "goalscorer",
)


def valid_price(value):
    try:
        if value is None or isinstance(value, bool):
            return False
        return float(value) != 0
    except (TypeError, ValueError):
        return False


def classify(row):
    book = str(row.get("bookmaker", "")).lower()
    market = (
        str(row.get("market", "")) + " " +
        str(row.get("market_key", ""))
    ).lower()

    odds_type = str(row.get("odds_type", "")).lower()
    projection = str(row.get("projection_type", "")).upper()

    if (
        book in DFS_BOOKS
        or row.get("is_dfs_flat_payout") is True
        or row.get("dfs_normalized") is True
        or odds_type in ("goblin", "demon")
        or projection in ("GOBLIN", "DEMON")
    ):
        return "dfs_or_adjusted_projection"

    if book in EXCHANGES:
        return "exchange_or_prediction_market"

    if any(term in market for term in SINGLE_OUTCOME_TERMS):
        return "single_outcome_market"

    over = valid_price(row.get("over_price"))
    under = valid_price(row.get("under_price"))

    if over and under:
        if book in SPORTSBOOKS:
            return "two_sided_sportsbook_candidate"
        return "two_sided_other_source"

    if over or under:
        return "one_sided_or_incomplete"

    return "no_usable_prices"


def main():
    if not SOURCE.exists():
        raise SystemExit("Snapshot not found.")

    with SOURCE.open(encoding="utf-8") as file:
        snapshot = json.load(file)

    counts = Counter()
    books = Counter()
    sports = Counter()

    for result in snapshot.get("results", []):
        sport = result.get("sport", "unknown")

        for row in result.get("rows", []):
            if not isinstance(row, dict):
                continue

            category = classify(row)

            counts[category] += 1
            books[str(row.get("bookmaker", "unknown"))] += 1
            sports[sport] += 1

    lines = [
        "# Prop Data Classification",
        "",
        f"Snapshot: {snapshot.get('collected_at')}",
        f"Total classified: {sum(counts.values())}",
        "",
        "Classification only. No bet is approved.",
        "",
        "## Categories",
        "",
    ]

    for name, count in counts.most_common():
        lines.append(f"- {name}: {count}")

    lines += ["", "## Sports", ""]

    for name, count in sports.most_common():
        lines.append(f"- {name}: {count}")

    lines += ["", "## Bookmakers", ""]

    for name, count in books.most_common():
        lines.append(f"- {name}: {count}")

    lines += [
        "",
        "## Important restrictions",
        "",
        "- DFS prices are not treated as ordinary sportsbook odds.",
        "- Single-outcome markets are not treated as Over/Under pairs.",
        "- One-sided prices cannot enter two-sided no-vig calculations.",
        "- Sportsbook candidates still require Ontario verification.",
        "- No model probabilities or positive EV are inferred.",
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("Classification completed.")
    print("Total:", sum(counts.values()))

    for name, count in counts.most_common():
        print(f"{name}: {count}")

    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
  
