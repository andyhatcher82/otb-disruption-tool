"""
generate_disruption_feed.py
Simulates a French ATC strike by reading flights.csv and producing
disruption_feed.json — a mock real-time disruption event payload.

Only flights departing within the disruption window appear in the output.
Flights absent from the disruptions array are treated as Scheduled/unaffected
by the consuming app.
"""
from __future__ import annotations
import csv
import json
import random
from datetime import date, datetime
from pathlib import Path

SEED = 77

FLIGHTS_FILE = Path(__file__).parent.parent / "dataFeeds" / "flights.csv"
OUTPUT_FILE  = Path(__file__).parent.parent / "dataFeeds" / "disruption_feed.json"

DISRUPTION_START = date(2026, 5, 2)
DISRUPTION_END   = date(2026, 5, 8)

LANDS_FRANCE    = {"NCE", "CDG", "LYS", "MRS"}
WESTERN_REROUTE = {"PMI", "IBZ", "AGP", "FAO", "TFS"}
EASTERN_REROUTE = {"MLA", "ATH", "HER", "LCA", "CFU", "RHO"}

STATUSES = ["Cancelled", "Rerouted", "Delayed", "Scheduled"]

# [Cancelled, Rerouted, Delayed, Scheduled] weights
WEIGHTS: dict[str, list[int]] = {
    "via_france":   [30, 20, 15, 35],
    "lands_france": [10,  0,  5, 85],
}


def classify(route_via: str, dest_iata: str) -> str:
    if dest_iata in LANDS_FRANCE:
        return "lands_france"
    if "France" in route_via.split("|"):
        return "via_france"
    return "unaffected"


def reroute_via(original: str, dest_iata: str) -> str:
    parts = original.split("|")
    if "France" not in parts:
        return original
    idx = parts.index("France")
    # Eastern Med: reroute via Germany (Italy and beyond already in chain)
    # Western Med + default: reroute down Atlantic coast
    replacement = "Germany" if dest_iata in EASTERN_REROUTE else "Atlantic Ocean"
    parts[idx] = replacement
    deduped = [parts[0]]
    for p in parts[1:]:
        if p != deduped[-1]:
            deduped.append(p)
    return "|".join(deduped)


def build_disruption(row: dict, rng: random.Random) -> dict | None:
    cat = classify(row["route_via"], row["destination_iata"])
    if cat == "unaffected":
        return None

    status = rng.choices(STATUSES, weights=WEIGHTS[cat], k=1)[0]
    if status == "Scheduled":
        return None

    new_route = None
    delay_min = None

    if status == "Rerouted":
        new_route = reroute_via(row["route_via"], row["destination_iata"])
        reason = "French ATC strike — flight rerouted to avoid French airspace"
    elif status == "Cancelled":
        reason = "French ATC strike — flight through French airspace cancelled"
    else:
        delay_min = rng.randint(60, 240)
        reason = "French ATC strike — departure delayed due to airspace congestion"

    return {
        "flight_number":      row["flight_number"],
        "disruption_status":  status,
        "original_route_via": row["route_via"],
        "new_route_via":      new_route,
        "delay_minutes":      delay_min,
        "reason":             reason,
    }


OPERATIONAL_CANCELLATIONS = [
    {"count": 2, "reason": "Flight cancelled due to mechanical fault — aircraft unserviceable"},
    {"count": 3, "reason": "Flight cancelled — crew maximum working hours reached, no replacement crew available"},
]


def main() -> None:
    rng = random.Random(SEED)
    disruptions: list[dict] = []
    scheduled_rows: list[dict] = []
    total_in_window = 0
    status_counts: dict[str, int] = {s: 0 for s in STATUSES}

    with open(FLIGHTS_FILE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            dep_date = date.fromisoformat(row["scheduled_departure_dt"][:10])
            if not (DISRUPTION_START <= dep_date <= DISRUPTION_END):
                continue
            total_in_window += 1
            result = build_disruption(row, rng)
            if result:
                disruptions.append(result)
                status_counts[result["disruption_status"]] += 1
            else:
                status_counts["Scheduled"] += 1
                scheduled_rows.append(row)

    # Add operational cancellations picked from otherwise-scheduled flights
    disrupted_fns = {d["flight_number"] for d in disruptions}
    candidates = [r for r in scheduled_rows if r["flight_number"] not in disrupted_fns]
    rng.shuffle(candidates)
    pick_idx = 0
    for op in OPERATIONAL_CANCELLATIONS:
        for _ in range(op["count"]):
            if pick_idx >= len(candidates):
                break
            row = candidates[pick_idx]
            pick_idx += 1
            disruptions.append({
                "flight_number":      row["flight_number"],
                "disruption_status":  "Cancelled",
                "original_route_via": row["route_via"],
                "new_route_via":      None,
                "delay_minutes":      None,
                "reason":             op["reason"],
            })
            status_counts["Cancelled"] += 1
            status_counts["Scheduled"] -= 1

    payload = {
        "event": {
            "id": "ATC_FRANCE_20260502",
            "title": "French ATC Strike — French Airspace Restrictions",
            "description": (
                "Industrial action by French air traffic controllers. "
                "French airspace capacity reduced to ~50%. "
                "Flights landing in France prioritised (90% unaffected). "
                "Approximately 30% of through-France flights cancelled; 20% rerouted."
            ),
            "disruption_start": str(DISRUPTION_START),
            "disruption_end":   str(DISRUPTION_END),
            "generated_at":     datetime.now().strftime("%Y-%m-%dT%H:%M"),
        },
        "disruptions": disruptions,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"\nDisruption feed written to {OUTPUT_FILE}")
    print(f"Flights in window ({DISRUPTION_START} to {DISRUPTION_END}): {total_in_window}")
    print("\nStatus breakdown:")
    for s in STATUSES:
        n = status_counts[s]
        pct = n / total_in_window * 100 if total_in_window else 0
        print(f"  {s:<12} {n:>4}  ({pct:.0f}%)")
    print(f"\nDisruption records in feed: {len(disruptions)}")

    # Spot-check verification
    rerouted = [d for d in disruptions if d["disruption_status"] == "Rerouted"]
    if rerouted:
        bad = [d for d in rerouted if d["new_route_via"] and "France" in d["new_route_via"].split("|")]
        print(f"\nRerouted flights with France still in new route: {len(bad)}  (expect 0)")


if __name__ == "__main__":
    main()
