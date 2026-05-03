"""
generate_flights.py
Generates the master flight schedule for the OTB Flight Disruption Tool.

Reads bookings.csv to extract every referenced flight (outbound + return),
then adds ~300 extra flights across existing and new routes to simulate a
busy August-peak schedule. Run once to produce flights.csv.
"""
from __future__ import annotations
import csv
import random
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

SEED = 99
random.seed(SEED)

TODAY          = datetime(2026, 5, 2, 0, 0, 0)
BOOKINGS_FILE  = Path(__file__).parent.parent / "dataFeeds" / "bookings.csv"
OUTPUT_FILE    = Path(__file__).parent.parent / "dataFeeds" / "flights.csv"
TARGET_FLIGHTS = 2500

# ---------------------------------------------------------------------------
# Reference data (kept self-contained — not imported from generate_bookings)
# ---------------------------------------------------------------------------

AIRLINES = [
    ("EasyJet",          "EZY"),
    ("Ryanair",          "FR"),
    ("Jet2",             "LS"),
    ("British Airways",  "BA"),
    ("TUI",              "BY"),
    ("Emirates",         "EK"),
    ("Aer Lingus",       "EI"),
    ("Wizz Air",         "W6"),
    ("Delta Airlines",   "DL"),
    ("American Airlines","AA"),
    ("KLM",              "KL"),
]

AIRPORT_NAMES = {
    # UK origins
    "MAN": "Manchester",       "LGW": "London Gatwick",   "LHR": "London Heathrow",
    "STN": "London Stansted",  "BHX": "Birmingham",       "EDI": "Edinburgh",
    "LBA": "Leeds Bradford",   "NCL": "Newcastle",        "BRS": "Bristol",
    "GLA": "Glasgow",          "BFS": "Belfast City",     "EMA": "East Midlands",
    "LTN": "London Luton",
    # Other origins
    "DUB": "Dublin",  "AMS": "Amsterdam",  "BCN": "Barcelona",  "FCO": "Rome Fiumicino",
    # Holiday destinations
    "MLA": "Malta",             "PMI": "Palma, Majorca",   "IBZ": "Ibiza",
    "TFS": "Tenerife",          "FAO": "Faro",             "AGP": "Malaga",
    "ATH": "Athens",            "HER": "Heraklion, Crete", "LCA": "Larnaca, Cyprus",
    "CFU": "Corfu",             "RHO": "Rhodes",
    "NCE": "Nice",              "CDG": "Paris",            "LYS": "Lyon",
    "MRS": "Marseille",
    "CUN": "Cancun",            "JFK": "New York",         "MIA": "Miami",
    "MCO": "Orlando",
    "DBV": "Dubrovnik",         "SPU": "Split",            "TIV": "Tivat",
    "SOF": "Sofia",             "KRK": "Krakow",
    "KEF": "Reykjavik",         "LIS": "Lisbon",
    "DXB": "Dubai",             "BKK": "Bangkok",          "HKG": "Hong Kong",
    "WAW": "Warsaw",            "BUD": "Budapest",         "PRG": "Prague",
}

ORIGIN_COUNTRY = {
    "MAN": "England",         "LGW": "England",    "LHR": "England",
    "STN": "England",         "BHX": "England",    "EDI": "Scotland",
    "LBA": "England",         "NCL": "England",    "BRS": "England",
    "GLA": "Scotland",        "BFS": "Northern Ireland",
    "EMA": "England",         "LTN": "England",
    "DUB": "Ireland",         "AMS": "Netherlands",
    "BCN": "Spain",           "FCO": "Italy",
}

ALL_ORIGINS = list(ORIGIN_COUNTRY.keys())

# Destinations pool — used for generating extra flights on new routes
# via_countries: countries overflown BETWEEN origin and destination
DESTINATIONS = [
    # Passes over France
    {"iata": "MLA", "name": "Malta",            "dest_country": "Malta",           "via": ["France", "Italy"],           "flight_h": (3.0, 4.0)},
    {"iata": "PMI", "name": "Palma, Majorca",   "dest_country": "Spain",           "via": ["France"],                    "flight_h": (2.0, 3.0)},
    {"iata": "IBZ", "name": "Ibiza",            "dest_country": "Spain",           "via": ["France"],                    "flight_h": (2.0, 3.0)},
    {"iata": "TFS", "name": "Tenerife",         "dest_country": "Canary Islands",  "via": ["France", "Spain"],           "flight_h": (4.0, 5.0)},
    {"iata": "FAO", "name": "Faro",             "dest_country": "Portugal",        "via": ["France", "Spain"],           "flight_h": (2.0, 3.0)},
    {"iata": "AGP", "name": "Malaga",           "dest_country": "Spain",           "via": ["France"],                    "flight_h": (2.0, 3.0)},
    {"iata": "ATH", "name": "Athens",           "dest_country": "Greece",          "via": ["France", "Italy"],           "flight_h": (3.0, 4.0)},
    {"iata": "HER", "name": "Heraklion, Crete", "dest_country": "Greece",          "via": ["France", "Italy"],           "flight_h": (4.0, 5.0)},
    {"iata": "LCA", "name": "Larnaca, Cyprus",  "dest_country": "Cyprus",          "via": ["France", "Italy", "Greece"], "flight_h": (4.0, 5.0)},
    {"iata": "CFU", "name": "Corfu",            "dest_country": "Greece",          "via": ["France", "Italy"],           "flight_h": (3.0, 4.0)},
    {"iata": "RHO", "name": "Rhodes",           "dest_country": "Greece",          "via": ["France", "Italy"],           "flight_h": (4.0, 5.0)},
    # Lands in France
    {"iata": "NCE", "name": "Nice",             "dest_country": "France",          "via": [],                            "flight_h": (2.0, 3.0)},
    {"iata": "CDG", "name": "Paris",            "dest_country": "France",          "via": [],                            "flight_h": (1.0, 2.0)},
    {"iata": "LYS", "name": "Lyon",             "dest_country": "France",          "via": [],                            "flight_h": (1.0, 2.0)},
    {"iata": "MRS", "name": "Marseille",        "dest_country": "France",          "via": [],                            "flight_h": (2.0, 3.0)},
    # Transatlantic
    {"iata": "CUN", "name": "Cancun",           "dest_country": "Mexico",          "via": ["Atlantic Ocean"],            "flight_h": (10.0, 11.0)},
    {"iata": "JFK", "name": "New York",         "dest_country": "USA",             "via": ["Atlantic Ocean"],            "flight_h": (7.0, 8.0)},
    {"iata": "MIA", "name": "Miami",            "dest_country": "USA",             "via": ["Atlantic Ocean"],            "flight_h": (9.0, 10.0)},
    {"iata": "MCO", "name": "Orlando",          "dest_country": "USA",             "via": ["Atlantic Ocean"],            "flight_h": (9.0, 10.0)},
    # Eastern Europe
    {"iata": "DBV", "name": "Dubrovnik",        "dest_country": "Croatia",         "via": ["Germany", "Austria"],        "flight_h": (2.0, 3.0)},
    {"iata": "SPU", "name": "Split",            "dest_country": "Croatia",         "via": ["Germany", "Austria"],        "flight_h": (2.0, 3.0)},
    {"iata": "TIV", "name": "Tivat",            "dest_country": "Montenegro",      "via": ["Germany", "Austria"],        "flight_h": (3.0, 4.0)},
    {"iata": "SOF", "name": "Sofia",            "dest_country": "Bulgaria",        "via": ["Germany", "Austria"],        "flight_h": (3.0, 4.0)},
    {"iata": "KRK", "name": "Krakow",           "dest_country": "Poland",          "via": ["Germany"],                   "flight_h": (2.0, 3.0)},
    {"iata": "WAW", "name": "Warsaw",           "dest_country": "Poland",          "via": ["Germany"],                   "flight_h": (2.0, 3.0)},
    {"iata": "BUD", "name": "Budapest",         "dest_country": "Hungary",         "via": ["Germany"],                   "flight_h": (2.0, 3.0)},
    {"iata": "PRG", "name": "Prague",           "dest_country": "Czech Republic",  "via": ["Germany"],                   "flight_h": (2.0, 3.0)},
    # Short-haul
    {"iata": "AMS", "name": "Amsterdam",        "dest_country": "Netherlands",     "via": [],                            "flight_h": (1.0, 2.0)},
    {"iata": "DUB", "name": "Dublin",           "dest_country": "Ireland",         "via": [],                            "flight_h": (1.0, 2.0)},
    {"iata": "KEF", "name": "Reykjavik",        "dest_country": "Iceland",         "via": ["Atlantic Ocean"],            "flight_h": (2.0, 3.0)},
    {"iata": "LIS", "name": "Lisbon",           "dest_country": "Portugal",        "via": ["Atlantic Ocean"],            "flight_h": (2.0, 3.0)},
    # Middle East / Far East (not over France)
    {"iata": "DXB", "name": "Dubai",            "dest_country": "United Arab Emirates", "via": ["Turkey", "Saudi Arabia"], "flight_h": (7.0, 8.0)},
    {"iata": "BKK", "name": "Bangkok",          "dest_country": "Thailand",        "via": ["Turkey", "India"],           "flight_h": (11.0, 12.0)},
    {"iata": "HKG", "name": "Hong Kong",        "dest_country": "China",           "via": ["Turkey", "India"],           "flight_h": (12.0, 13.0)},
]

DEST_BY_IATA = {d["iata"]: d for d in DESTINATIONS}

# Origins already south of/in France — French airspace not on their flight paths
SOUTHERN_ORIGINS = {"BCN", "FCO"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_route_via(origin_iata: str, dest_iata: str) -> str:
    origin_country = ORIGIN_COUNTRY.get(origin_iata, "England")
    dest           = DEST_BY_IATA.get(dest_iata)
    if dest is None:
        return origin_country
    via = [c for c in dest["via"] if c != "France"] if origin_iata in SOUTHERN_ORIGINS else dest["via"]
    countries = [origin_country] + via + [dest["dest_country"]]
    deduped   = [countries[0]]
    for c in countries[1:]:
        if c != deduped[-1]:
            deduped.append(c)
    return "|".join(deduped)


def assign_aircraft(duration_h: float) -> tuple[str, int]:
    if duration_h <= 2.0:
        aircraft = random.choice(["Airbus A320", "Boeing 737-800"])
        capacity = random.randint(150, 180)
    elif duration_h <= 4.0:
        aircraft = random.choice(["Airbus A320", "Boeing 737-800", "Airbus A321"])
        capacity = random.randint(160, 215)
    elif duration_h <= 6.0:
        aircraft = random.choice(["Airbus A321", "Boeing 737 MAX"])
        capacity = random.randint(195, 225)
    else:
        aircraft = random.choice(["Boeing 787-9", "Airbus A330-300"])
        capacity = random.randint(270, 300)
    return aircraft, capacity


def make_flight_number(code: str, used: set) -> str:
    while True:
        fn = f"{code}{random.randint(1000, 9999)}"
        if fn not in used:
            used.add(fn)
            return fn


def random_departure_time(base_date: datetime) -> datetime:
    hour   = random.randint(5, 22)
    minute = random.choice([0, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


def flight_row(fn, airline, origin, dest_iata, dest_name, dep, arr, route_via, aircraft, capacity) -> dict:
    # August peak: 88-100% full, leaving 0-12% available seats
    available = random.randint(0, max(0, int(capacity * 0.12)))
    return {
        "flight_number":          fn,
        "airline":                airline,
        "origin_iata":            origin,
        "destination_iata":       dest_iata,
        "destination_name":       dest_name,
        "scheduled_departure_dt": dep.strftime("%Y-%m-%d %H:%M"),
        "scheduled_arrival_dt":   arr.strftime("%Y-%m-%d %H:%M"),
        "route_via":              route_via,
        "aircraft_type":          aircraft,
        "total_capacity":         capacity,
        "available_seats":        available,
        "flight_status":          "Scheduled",
    }


# ---------------------------------------------------------------------------
# Step 1 — extract flights already referenced in bookings.csv
# ---------------------------------------------------------------------------

def extract_booked_flights() -> tuple[list[dict], set]:
    flights: dict[str, dict] = {}

    with open(BOOKINGS_FILE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for prefix, ret_flag in [("outbound", False), ("return", True)]:
                fn  = row[f"{prefix}_flight_number"]
                dep_str = row[f"{'return' if ret_flag else 'outbound'}_departure_dt"]
                arr_str = row[f"{'return' if ret_flag else 'outbound'}_arrival_dt"]

                if not fn or not dep_str:
                    continue
                if fn in flights:
                    continue

                dep      = datetime.strptime(dep_str, "%Y-%m-%d %H:%M")
                arr      = datetime.strptime(arr_str, "%Y-%m-%d %H:%M")
                dur      = (arr - dep).total_seconds() / 3600
                aircraft, capacity = assign_aircraft(dur)
                origin   = row[f"{prefix}_origin"]
                dest_i   = row[f"{prefix}_destination"]

                flights[fn] = flight_row(
                    fn         = fn,
                    airline    = row[f"{prefix}_airline"],
                    origin     = origin,
                    dest_iata  = dest_i,
                    dest_name  = AIRPORT_NAMES.get(dest_i, dest_i),
                    dep        = dep,
                    arr        = arr,
                    route_via  = row[f"{prefix}_route_via"],
                    aircraft   = aircraft,
                    capacity   = capacity,
                )

    used = set(flights.keys())
    return list(flights.values()), used


# ---------------------------------------------------------------------------
# Step 2 — generate extra flights
# ---------------------------------------------------------------------------

def generate_extra_flights(booked: list[dict], used: set, count: int) -> list[dict]:
    # Build route pool from booked flights (origin, dest_iata) pairs
    booked_routes: list[tuple[str, str]] = list({
        (f["origin_iata"], f["destination_iata"]) for f in booked
    })

    # Build extra route pool: new origins × all destinations + all origins × new destinations
    new_origins = ["GLA", "BFS", "EMA", "LTN"]
    new_dest_iatas = {"WAW", "BUD", "PRG", "DXB", "BKK", "HKG"}
    extra_routes: set[tuple[str, str]] = set()

    for origin in new_origins:
        for dest in DESTINATIONS:
            extra_routes.add((origin, dest["iata"]))

    for origin in ALL_ORIGINS:
        for iata in new_dest_iatas:
            extra_routes.add((origin, iata))

    # Combined weighted pool: existing routes 3× more likely (busier, August peak)
    route_pool = booked_routes * 3 + list(extra_routes)

    extras: list[dict] = []
    while len(extras) < count:
        origin, dest_iata = random.choice(route_pool)
        dest = DEST_BY_IATA.get(dest_iata)
        if dest is None:
            continue

        airline_name, airline_code = random.choice(AIRLINES)
        dur_h  = random.uniform(*dest["flight_h"])
        base   = TODAY + timedelta(days=random.randint(-14, 14))
        dep    = random_departure_time(base)
        arr    = dep + timedelta(hours=int(dur_h), minutes=int((dur_h % 1) * 60))
        aircraft, capacity = assign_aircraft(dur_h)
        fn     = make_flight_number(airline_code, used)

        extras.append(flight_row(
            fn        = fn,
            airline   = airline_name,
            origin    = origin,
            dest_iata = dest_iata,
            dest_name = dest["name"],
            dep       = dep,
            arr       = arr,
            route_via = build_route_via(origin, dest_iata),
            aircraft  = aircraft,
            capacity  = capacity,
        ))

    return extras


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def print_summary(all_flights: list[dict]) -> None:
    total = len(all_flights)
    print(f"\nWritten {total} flights to {OUTPUT_FILE}\n")

    via_france  = sum(1 for f in all_flights if "France" in f["route_via"])
    atlantic    = sum(1 for f in all_flights if "Atlantic Ocean" in f["route_via"] and "France" not in f["route_via"])
    other       = total - via_france - atlantic

    print("Route categories:")
    print(f"  Involves French airspace : {via_france:>4}  ({via_france/total*100:.0f}%)")
    print(f"  Transatlantic            : {atlantic:>4}  ({atlantic/total*100:.0f}%)")
    print(f"  Other (no French/Atlantic): {other:>4}  ({other/total*100:.0f}%)")

    print("\nTop 5 aircraft types:")
    for ac, cnt in Counter(f["aircraft_type"] for f in all_flights).most_common(5):
        print(f"  {ac:<22} {cnt:>4}")


def main() -> None:
    booked, used = extract_booked_flights()
    extras       = generate_extra_flights(booked, used, TARGET_FLIGHTS - len(booked))
    all_flights  = booked + extras

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_flights[0].keys()))
        writer.writeheader()
        writer.writerows(all_flights)

    print_summary(all_flights)

    # Verify every booked flight number is present
    written = {r["flight_number"] for r in all_flights}
    missing = [f["flight_number"] for f in booked if f["flight_number"] not in written]
    if missing:
        print(f"\nWARNING: {len(missing)} booked flight(s) missing from output: {missing[:5]}")
    else:
        print(f"\nVerification passed: all {len(booked)} booked flights present in flights.csv")


if __name__ == "__main__":
    main()
