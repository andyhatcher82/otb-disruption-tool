"""
generate_bookings.py
Generates mock customer booking data for the OTB Flight Disruption Tool.
Run once to produce bookings.csv in the same directory.
"""
from __future__ import annotations
import csv
import random
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
random.seed(SEED)

TODAY = datetime(2026, 5, 2, 0, 0, 0)
TOTAL_BOOKINGS = 200
OUTPUT_FILE = Path(__file__).parent.parent / "dataFeeds" / "bookings.csv"

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

UK_AIRPORTS   = ["MAN", "LGW", "LHR", "STN", "BHX", "EDI", "LBA", "NCL", "BRS"]
OTHER_AIRPORTS = ["DUB", "AMS", "BCN", "FCO"]

ORIGIN_COUNTRY = {
    "MAN": "England",     "LGW": "England",  "LHR": "England",
    "STN": "England",     "BHX": "England",  "EDI": "Scotland",
    "LBA": "England",     "NCL": "England",  "BRS": "England",
    "DUB": "Ireland",     "AMS": "Netherlands",
    "BCN": "Spain",       "FCO": "Italy",
}

# cat: via_france | lands_france | atlantic | eastern_europe | short_haul
# via_countries: countries overflown BETWEEN origin and destination (exclusive of both)
DESTINATIONS = [
    # --- Passes over France (~50%) ---
    {"iata": "MLA", "name": "Malta",            "cat": "via_france",     "dest_country": "Malta",           "via_countries": ["France", "Italy"],           "flight_h": (3, 4)},
    {"iata": "PMI", "name": "Palma, Majorca",   "cat": "via_france",     "dest_country": "Spain",           "via_countries": ["France"],                    "flight_h": (2, 3)},
    {"iata": "IBZ", "name": "Ibiza",            "cat": "via_france",     "dest_country": "Spain",           "via_countries": ["France"],                    "flight_h": (2, 3)},
    {"iata": "TFS", "name": "Tenerife",         "cat": "via_france",     "dest_country": "Canary Islands",  "via_countries": ["France", "Spain"],           "flight_h": (4, 5)},
    {"iata": "FAO", "name": "Faro",             "cat": "via_france",     "dest_country": "Portugal",        "via_countries": ["France", "Spain"],           "flight_h": (2, 3)},
    {"iata": "AGP", "name": "Malaga",           "cat": "via_france",     "dest_country": "Spain",           "via_countries": ["France"],                    "flight_h": (2, 3)},
    {"iata": "ATH", "name": "Athens",           "cat": "via_france",     "dest_country": "Greece",          "via_countries": ["France", "Italy"],           "flight_h": (3, 4)},
    {"iata": "HER", "name": "Heraklion, Crete", "cat": "via_france",     "dest_country": "Greece",          "via_countries": ["France", "Italy"],           "flight_h": (4, 5)},
    {"iata": "LCA", "name": "Larnaca, Cyprus",  "cat": "via_france",     "dest_country": "Cyprus",          "via_countries": ["France", "Italy", "Greece"], "flight_h": (4, 5)},
    {"iata": "CFU", "name": "Corfu",            "cat": "via_france",     "dest_country": "Greece",          "via_countries": ["France", "Italy"],           "flight_h": (3, 4)},
    {"iata": "RHO", "name": "Rhodes",           "cat": "via_france",     "dest_country": "Greece",          "via_countries": ["France", "Italy"],           "flight_h": (4, 5)},
    # --- Lands in France (~10%) ---
    {"iata": "NCE", "name": "Nice",             "cat": "lands_france",   "dest_country": "France",          "via_countries": [],                            "flight_h": (2, 3)},
    {"iata": "CDG", "name": "Paris",            "cat": "lands_france",   "dest_country": "France",          "via_countries": [],                            "flight_h": (1, 2)},
    {"iata": "LYS", "name": "Lyon",             "cat": "lands_france",   "dest_country": "France",          "via_countries": [],                            "flight_h": (1, 2)},
    {"iata": "MRS", "name": "Marseille",        "cat": "lands_france",   "dest_country": "France",          "via_countries": [],                            "flight_h": (2, 3)},
    # --- Transatlantic, no French airspace (~15%) ---
    {"iata": "CUN", "name": "Cancun",           "cat": "atlantic",       "dest_country": "Mexico",          "via_countries": ["Atlantic Ocean"],            "flight_h": (10, 11)},
    {"iata": "JFK", "name": "New York",         "cat": "atlantic",       "dest_country": "USA",             "via_countries": ["Atlantic Ocean"],            "flight_h": (7, 8)},
    {"iata": "MIA", "name": "Miami",            "cat": "atlantic",       "dest_country": "USA",             "via_countries": ["Atlantic Ocean"],            "flight_h": (9, 10)},
    {"iata": "MCO", "name": "Orlando",          "cat": "atlantic",       "dest_country": "USA",             "via_countries": ["Atlantic Ocean"],            "flight_h": (9, 10)},
    # --- Eastern Europe, no French airspace (~10%) ---
    {"iata": "DBV", "name": "Dubrovnik",        "cat": "eastern_europe", "dest_country": "Croatia",         "via_countries": ["Germany", "Austria"],        "flight_h": (2, 3)},
    {"iata": "SPU", "name": "Split",            "cat": "eastern_europe", "dest_country": "Croatia",         "via_countries": ["Germany", "Austria"],        "flight_h": (2, 3)},
    {"iata": "TIV", "name": "Tivat",            "cat": "eastern_europe", "dest_country": "Montenegro",      "via_countries": ["Germany", "Austria"],        "flight_h": (3, 4)},
    {"iata": "SOF", "name": "Sofia",            "cat": "eastern_europe", "dest_country": "Bulgaria",        "via_countries": ["Germany", "Austria"],        "flight_h": (3, 4)},
    {"iata": "KRK", "name": "Krakow",           "cat": "eastern_europe", "dest_country": "Poland",          "via_countries": ["Germany"],                   "flight_h": (2, 3)},
    # --- Short-haul, no French airspace (~15%) ---
    {"iata": "AMS", "name": "Amsterdam",        "cat": "short_haul",     "dest_country": "Netherlands",     "via_countries": [],                            "flight_h": (1, 2)},
    {"iata": "DUB", "name": "Dublin",           "cat": "short_haul",     "dest_country": "Ireland",         "via_countries": [],                            "flight_h": (1, 2)},
    {"iata": "KEF", "name": "Reykjavik",        "cat": "short_haul",     "dest_country": "Iceland",         "via_countries": ["Atlantic Ocean"],            "flight_h": (2, 3)},
    {"iata": "LIS", "name": "Lisbon",           "cat": "short_haul",     "dest_country": "Portugal",        "via_countries": ["Atlantic Ocean"],            "flight_h": (2, 3)},
]

CATEGORY_WEIGHTS = {
    "via_france":     50,
    "lands_france":   10,
    "atlantic":       15,
    "eastern_europe": 10,
    "short_haul":     15,
}

FIRST_NAMES = [
    "James", "Oliver", "Harry", "Jack", "George", "Noah", "Charlie", "Jacob", "Alfie", "Freddie",
    "Emma", "Olivia", "Isla", "Ava", "Mia", "Isabella", "Sophie", "Lily", "Grace", "Amelia",
    "Mohammed", "Daniel", "Liam", "William", "Benjamin", "Lucas", "Ethan", "Logan", "Thomas", "Joshua",
    "Charlotte", "Hannah", "Chloe", "Ella", "Emily", "Sophia", "Jessica", "Ruby", "Poppy", "Ellie",
    "Samuel", "Ryan", "Luke", "Matthew", "Andrew", "Patrick", "Sean", "Nathan", "Adam", "Michael",
    "Sarah", "Laura", "Katie", "Amy", "Rebecca", "Victoria", "Claire", "Helen", "Susan", "Karen",
]

LAST_NAMES = [
    "Smith", "Jones", "Williams", "Taylor", "Brown", "Davies", "Evans", "Wilson", "Thomas", "Roberts",
    "Johnson", "Walker", "Wright", "Robinson", "Thompson", "White", "Hughes", "Edwards", "Green", "Hall",
    "Lewis", "Harris", "Clarke", "Patel", "Jackson", "Wood", "Turner", "Martin", "Cooper", "Hill",
    "Ward", "Morris", "Moore", "Clark", "Lee", "King", "Baker", "Harrison", "Morgan", "Allen",
    "Scott", "Young", "Mitchell", "Anderson", "Phillips", "Carter", "Murphy", "O'Brien", "Walsh", "Ryan",
    "Khan", "Ahmed", "Ali", "Singh", "Sharma", "Campbell", "Stewart", "Reid", "Murray", "Henderson",
]

HOTEL_ADJECTIVES = [
    "Sunrise", "Golden", "Blue", "Royal", "Grand", "Palm", "Coral", "Sunset", "Ocean", "Mediterranean",
    "Azure", "Horizon", "Breeze", "Pearl", "Amber", "Starlight", "Serenity", "Paradise", "Crystal", "Ivory",
]
HOTEL_TYPES = [
    "Hotel", "Resort", "Beach Hotel", "Apartments", "Suites", "Beach Club",
    "Holiday Village", "Hotel & Spa", "Beach Resort", "All-Inclusive Resort",
]


def build_route_via(origin_iata: str, dest: dict) -> str:
    origin_country = ORIGIN_COUNTRY.get(origin_iata, "England")
    countries = [origin_country] + dest["via_countries"] + [dest["dest_country"]]
    # Remove consecutive duplicates (e.g. if origin already matches a via country)
    deduped = [countries[0]]
    for c in countries[1:]:
        if c != deduped[-1]:
            deduped.append(c)
    return "|".join(deduped)


def build_return_route_via(origin_iata: str, dest: dict) -> str:
    return "|".join(reversed(build_route_via(origin_iata, dest).split("|")))


def make_hotel_name(dest_name: str) -> str:
    city = dest_name.split(",")[0]
    return f"{random.choice(HOTEL_ADJECTIVES)} {city} {random.choice(HOTEL_TYPES)}"


def make_flight_number(code: str) -> str:
    return f"{code}{random.randint(1000, 9999)}"


def make_booking_ref(used: set) -> str:
    while True:
        ref = f"OTB-{random.randint(10000, 99999)}"
        if ref not in used:
            used.add(ref)
            return ref


def make_email(first: str, last: str) -> str:
    domains = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.co.uk", "icloud.com", "btinternet.com"]
    sep = random.choice([".", "_", ""])
    num = str(random.randint(1, 99)) if random.random() < 0.3 else ""
    return f"{first.lower()}{sep}{last.lower()}{num}@{random.choice(domains)}"


def make_phone() -> str:
    return f"07{random.randint(100000000, 999999999)}"


def pick_destination() -> dict:
    cats    = list(CATEGORY_WEIGHTS.keys())
    weights = list(CATEGORY_WEIGHTS.values())
    cat = random.choices(cats, weights=weights, k=1)[0]
    return random.choice([d for d in DESTINATIONS if d["cat"] == cat])


def random_departure_time(base_date: datetime) -> datetime:
    hour   = random.randint(5, 22)
    minute = random.choice([0, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


def generate_bookings() -> list[dict]:
    used_refs: set = set()
    rows: list[dict] = []

    status_choices = ["Pre-departure", "Currently Travelling", "Returned"]
    status_weights  = [60, 25, 15]

    for _ in range(TOTAL_BOOKINGS):
        status = random.choices(status_choices, weights=status_weights, k=1)[0]
        dest   = pick_destination()
        airline_name, airline_code = random.choice(AIRLINES)

        origin = random.choice(UK_AIRPORTS if random.random() < 0.85 else OTHER_AIRPORTS)

        if status == "Pre-departure":
            outbound_date = TODAY + timedelta(days=random.randint(1, 14))
            return_date   = outbound_date + timedelta(days=random.randint(3, 21))
        elif status == "Currently Travelling":
            outbound_date = TODAY - timedelta(days=random.randint(1, 21))
            return_date   = TODAY + timedelta(days=random.randint(1, 14))
        else:  # Returned
            return_date   = TODAY - timedelta(days=random.randint(1, 14))
            outbound_date = return_date - timedelta(days=random.randint(3, 21))

        flight_hours = random.randint(*dest["flight_h"])
        outbound_dep = random_departure_time(outbound_date)
        outbound_arr = outbound_dep + timedelta(hours=flight_hours)
        return_dep   = random_departure_time(return_date)
        return_arr   = return_dep + timedelta(hours=flight_hours)

        # One-way trips (~5%); not applicable for Currently Travelling
        is_one_way = (status != "Currently Travelling") and (random.random() < 0.05)

        # Return airline: same as outbound 80% of the time
        if is_one_way:
            ret_name, ret_code = "", ""
        elif random.random() < 0.8:
            ret_name, ret_code = airline_name, airline_code
        else:
            ret_name, ret_code = random.choice(AIRLINES)

        first = random.choice(FIRST_NAMES)
        last  = random.choice(LAST_NAMES)

        rows.append({
            "booking_ref":              make_booking_ref(used_refs),
            "lead_passenger_last_name":  last,
            "lead_passenger_first_names":first,
            "lead_passenger_email":     make_email(first, last),
            "lead_passenger_phone":     make_phone(),
            "num_passengers":           random.choices(
                                            [1, 2, 3, 4, 5, 6, 7, 8],
                                            weights=[15, 40, 15, 15, 7, 5, 2, 1], k=1
                                        )[0],
            "outbound_flight_number":   make_flight_number(airline_code),
            "outbound_airline":         airline_name,
            "outbound_origin":          origin,
            "outbound_destination":     dest["iata"],
            "outbound_destination_name":dest["name"],
            "outbound_departure_dt":    outbound_dep.strftime("%Y-%m-%d %H:%M"),
            "outbound_arrival_dt":      outbound_arr.strftime("%Y-%m-%d %H:%M"),
            "outbound_route_via":       build_route_via(origin, dest),
            "return_flight_number":     make_flight_number(ret_code) if not is_one_way else "",
            "return_airline":           ret_name,
            "return_origin":            dest["iata"],
            "return_destination":       origin,
            "return_departure_dt":      return_dep.strftime("%Y-%m-%d %H:%M") if not is_one_way else "",
            "return_arrival_dt":        return_arr.strftime("%Y-%m-%d %H:%M") if not is_one_way else "",
            "return_route_via":         build_return_route_via(origin, dest) if not is_one_way else "",
            "hotel_name":               make_hotel_name(dest["name"]),
            "booking_status":           "Active",
            "travel_status":            status,
        })

    return rows


def print_summary(rows: list[dict]) -> None:
    total = len(rows)
    print(f"\nGenerated {total} bookings -> {OUTPUT_FILE}\n")

    print("Travel status distribution:")
    for status, count in Counter(r["travel_status"] for r in rows).most_common():
        print(f"  {status:<22} {count:>3}  ({count/total*100:.0f}%)")

    print("\nOutbound route category:")
    cats = Counter()
    for r in rows:
        via = r["outbound_route_via"]
        dest_iata = r["outbound_destination"]
        lands_france = ["NCE", "CDG", "LYS", "MRS"]
        if dest_iata in lands_france:
            cats["Lands in France"] += 1
        elif "France" in via:
            cats["Passes over France"] += 1
        elif "Atlantic Ocean" in via:
            cats["Transatlantic"] += 1
        else:
            cats["No French airspace"] += 1
    for cat, count in cats.most_common():
        print(f"  {cat:<22} {count:>3}  ({count/total*100:.0f}%)")

    one_way = sum(1 for r in rows if not r["return_departure_dt"])
    print(f"\n  One-way trips: {one_way}")


def main() -> None:
    rows = generate_bookings()

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print_summary(rows)


if __name__ == "__main__":
    main()
