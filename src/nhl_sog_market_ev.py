"""Weighted empirical NHL SOG probabilities and market EV calculator."""
import argparse, csv, math
from datetime import date
from pathlib import Path

def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def weighted_outcome_probabilities(history, line, half_life=10):
    if not history:
        raise ValueError("At least one prior game is required")
    if not math.isfinite(float(line)) or float(line) < 0:
        raise ValueError("Line must be finite and non-negative")
    if not math.isfinite(float(half_life)) or float(half_life) <= 0:
        raise ValueError("Half-life must be positive and finite")
    weights = [0.5 ** ((len(history)-1-i)/float(half_life)) for i in range(len(history))]
    total = sum(weights)
    over = sum(w for x,w in zip(history,weights) if x > line)
    under = sum(w for x,w in zip(history,weights) if x < line)
    push = sum(w for x,w in zip(history,weights) if x == line)
    return {"over_probability": over/total, "under_probability": under/total, "push_probability": push/total}

def decimal_odds_metrics(win_probability, push_probability, decimal_odds):
    odds = float(decimal_odds)
    if not math.isfinite(odds) or odds <= 1:
        raise ValueError("Decimal odds must be greater than 1.0")
    if not 0 <= win_probability <= 1 or not 0 <= push_probability <= 1 or win_probability+push_probability > 1+1e-12:
        raise ValueError("Invalid win/push probabilities")
    return 1/odds, 100*(win_probability*(odds-1) - (1-win_probability-push_probability))

def evaluate_markets(game_rows, market_rows, half_life=10):
    grouped = {}
    for r in game_rows:
        try:
            player = r["player"].strip()
            d = date.fromisoformat(r["game_date"])
            shots = int(r["shots_on_goal"])
        except (KeyError, AttributeError, TypeError, ValueError):
            raise ValueError("Game logs need player, valid game_date and shots_on_goal")
        if not player or shots < 0:
            raise ValueError("Player cannot be blank and shots cannot be negative")
        grouped.setdefault(player, []).append((d,shots))
    for p in grouped:
        grouped[p].sort()
    out = []
    for m in market_rows:
        try:
            player = m["player"].strip()
            target = date.fromisoformat(m["game_date"])
            line = float(m["line"])
            over_odds, under_odds = float(m["over_decimal_odds"]), float(m["under_decimal_odds"])
        except (KeyError, AttributeError, TypeError, ValueError):
            raise ValueError("Market CSV needs player, game_date, line, over_decimal_odds, under_decimal_odds")
        history = [s for d,s in grouped.get(player,[]) if d < target]
        row = {"player":player,"game_date":target.isoformat(),"line":line,"history_games":len(history)}
        if not history:
            row.update({"over_probability":"","under_probability":"","push_probability":"","over_implied_probability":"","under_implied_probability":"","over_ev_per_100":"","under_ev_per_100":"","best_side":"NO HISTORY"})
        else:
            p = weighted_outcome_probabilities(history,line,half_life)
            oi, oe = decimal_odds_metrics(p["over_probability"],p["push_probability"],over_odds)
            ui, ue = decimal_odds_metrics(p["under_probability"],p["push_probability"],under_odds)
            best = "OVER" if oe > 0 and oe > ue else "UNDER" if ue > 0 and ue > oe else "NO POSITIVE EDGE"
            row.update({k:round(v,6) for k,v in p.items()})
            row.update({"over_implied_probability":round(oi,6),"under_implied_probability":round(ui,6),"over_ev_per_100":round(oe,2),"under_ev_per_100":round(ue,2),"best_side":best})
        out.append(row)
    return out

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("game_logs"); ap.add_argument("markets")
    ap.add_argument("--half-life",type=float,default=10)
    ap.add_argument("--output",default="reports/nhl_sog/nhl_sog_market_ev.csv")
    a=ap.parse_args()
    rows=evaluate_markets(load_csv(a.game_logs),load_csv(a.markets),a.half_life)
    p=Path(a.output); p.parent.mkdir(parents=True,exist_ok=True)
    fields=["player","game_date","line","history_games","over_probability","under_probability","push_probability","over_implied_probability","under_implied_probability","over_ev_per_100","under_ev_per_100","best_side"]
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f"Markets evaluated: {len(rows)}"); print(f"Results saved to: {p}")

if __name__ == "__main__":
    main()
