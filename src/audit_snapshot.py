
"""Audit ParlayAPI snapshot structure without exposing API credentials."""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "reports" / "props_snapshot.json"


def main():
    if not SNAPSHOT.exists():
        raise SystemExit("Snapshot not found. Run the collector first.")

    with SNAPSHOT.open(encoding="utf-8") as file:
        data = json.load(file)

    print("=" * 60)
    print("ONTARIO PLAYER PROP DATA AUDIT")
    print("=" * 60)

    print("Provider:", data.get("provider"))
    print("Collected:", data.get("collected_at"))

    results = data.get("results", [])

    total_rows = 0
    sports = Counter()
    bookmakers = Counter()
    fields = Counter()
    markets = Counter()
    sample_rows = []

    for result in results:
        sport = result.get("sport", "unknown")
        rows = result.get("rows", [])

        sports[sport] += len(rows)
        total_rows += len(rows)

        print(f"\nSPORT: {sport}")
        print("HTTP status:", result.get("http_status"))
        print("Rows:", len(rows))
        print("Has more:", result.get("has_more"))
        print("Truncated:", result.get("truncated"))
        print("Degraded sources:", result.get("degraded_sources"))

        for row in rows:
            if not isinstance(row, dict):
                continue

            fields.update(row.keys())

            bookmaker = (
                row.get("bookmaker")
                or row.get("sportsbook")
                or row.get("operator")
                or "UNKNOWN"
            )
            bookmakers[str(bookmaker)] += 1

            market = (
                row.get("market")
                or row.get("market_name")
                or row.get("prop")
                or "UNKNOWN"
            )
            markets[str(market)] += 1

            if len(sample_rows) < 5:
                sample_rows.append(row)

    print("\n" + "=" * 60)
    print("TOTAL REFERENCE ROWS:", total_rows)

    print("\nRECORDS BY SPORT")
    for name, count in sports.most_common():
        print(f"{name}: {count}")

    print("\nTOP BOOKMAKERS")
    for name, count in bookmakers.most_common(20):
        print(f"{name}: {count}")

    print("\nTOP MARKETS")
    for name, count in markets.most_common(20):
        print(f"{name}: {count}")

    print("\nAVAILABLE DATA FIELDS")
    for name, count in fields.most_common():
        print(f"{name}: {count}")

    print("\nREDACTED SAMPLE STRUCTURE")

    for number, row in enumerate(sample_rows, 1):
        safe_row = {
            key: value
            for key, value in row.items()
            if not any(
                word in key.lower()
                for word in ("token", "secret", "key", "password")
            )
        }

        print(f"\nSAMPLE {number}")
        print(json.dumps(safe_row, indent=2)[:4000])

    print("\nAUDIT COMPLETE")


if __name__ == "__main__":
    main()
  
