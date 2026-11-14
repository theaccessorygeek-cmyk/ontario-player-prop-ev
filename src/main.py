
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.ev import (
    no_vig_probabilities,
    expected_value_per_dollar
)

from src.validation import validate_quote


ROOT = Path(__file__).resolve().parents[1]

TORONTO = ZoneInfo("America/Toronto")


def load_json(path, default):
    if not path.exists():
        return default

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def evaluate_quote(quote, now, operators):

    errors = validate_quote(
        quote,
        now,
        operators
    )

    if errors:
        return {
            "quote": quote,
            "errors": errors,
            "qualifies": False
        }

    over_probability, under_probability = (
        no_vig_probabilities(
            quote["over_american"],
            quote["under_american"]
        )
    )

    model_over = float(
        quote["model_probability"]
    )

    push = float(
        quote.get("push_probability", 0)
    )

    model_under = 1 - model_over - push

    over_ev = expected_value_per_dollar(
        model_over,
        quote["over_american"],
        push
    )

    under_ev = expected_value_per_dollar(
        model_under,
        quote["under_american"],
        push
    )

    over_edge = model_over - over_probability
    under_edge = model_under - under_probability

    if over_ev >= under_ev:
        best_side = "OVER"
        best_ev = over_ev
        best_edge = over_edge
    else:
        best_side = "UNDER"
        best_ev = under_ev
        best_edge = under_edge

    qualifies = (
        best_ev > 0
        and best_edge >= 0.05
    )

    return {
        "quote": quote,
        "errors": [],
        "best_side": best_side,
        "best_ev": best_ev,
        "best_edge": best_edge,
        "over_probability": over_probability,
        "under_probability": under_probability,
        "over_ev": over_ev,
        "under_ev": under_ev,
        "qualifies": qualifies
    }


def generate_report():

    now = datetime.now(TORONTO)

    config = load_json(
        ROOT / "config" / "books.json",
        {"candidate_operators": []}
    )

    quotes = load_json(
        ROOT / "data" / "quotes.json",
        []
    )

    operators = set(
        config["candidate_operators"]
    )

    results = []

    for quote in quotes:
        results.append(
            evaluate_quote(
                quote,
                now,
                operators
            )
        )

    report = []

    report.append(
        "# Ontario Player Prop EV Report"
    )

    report.append("")
    report.append(f"Generated: {now.isoformat()}")
    report.append("")
    report.append(
        "**Research only. No automatic bet placement.**"
    )

    report.append("")

    if not results:

        report.append(
            "## NO VERIFIED PRICES SUPPLIED"
        )

        report.append("")
        report.append(
            "No quote records were supplied."
        )

        report.append(
            "This does not mean there are no profitable markets."
        )

        report.append("")
        report.append(
            "**No qualifying bets. Suggested exposure: C$0.**"
        )

    else:

        qualified = [
            result for result in results
            if result["qualifies"]
        ]

        report.append(
            f"Candidates reviewed: {len(results)}"
        )

        report.append(
            f"Candidates passing all checks: {len(qualified)}"
        )

        report.append("")

        for number, result in enumerate(results, 1):

            quote = result["quote"]

            report.append(
                f"## {number}. {quote['player']} — "
                f"{quote['market']} {quote['line']}"
            )

            report.append(
                f"Event: {quote['event']}"
            )

            report.append(
                f"Sport: {quote['sport']}"
            )

            report.append(
                f"Bookmaker: {quote['operator']}"
            )

            report.append(
                f"Source: {quote['source_url']}"
            )

            if result["errors"]:

                report.append(
                    "**UNVERIFIED — NO BET**"
                )

                for error in result["errors"]:
                    report.append(f"- {error}")

            else:

                report.append(
                    f"No-vig over probability: "
                    f"{result['over_probability']:.1%}"
                )

                report.append(
                    f"No-vig under probability: "
                    f"{result['under_probability']:.1%}"
                )

                report.append(
                    f"Best side: {result['best_side']}"
                )

                report.append(
                    f"Estimated edge: "
                    f"{result['best_edge']:.1%}"
                )

                report.append(
                    f"Expected value per C$1: "
                    f"{result['best_ev']:+.3f}"
                )

                if result["qualifies"]:

                    report.append(
                        "**PASSES AUTOMATED EV FILTER — REVIEW REQUIRED**"
                    )

                else:

                    report.append(
                        "**NO BET — DOES NOT MEET EV REQUIREMENTS**"
                    )

            report.append("")

        if not qualified:

            report.append("## FINAL DECISION")

            report.append(
                "**NO QUALIFYING BETS. Suggested exposure: C$0.**"
            )

        else:

            report.append(
                "## FINAL DECISION"
            )

            report.append(
                "Candidates passed the mechanical checks. "
                "Independently verify all information before "
                "considering any wager."
            )

    report.append("")
    report.append(
        "This report depends on the quality of the supplied "
        "quotes and model probabilities."
    )

    output = ROOT / "reports" / "latest.md"

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output.write_text(
        "\n".join(report),
        encoding="utf-8"
    )

    print(f"Report created: {output}")


if __name__ == "__main__":
    generate_report()
  
