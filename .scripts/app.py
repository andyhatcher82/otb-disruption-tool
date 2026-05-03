"""
app.py  —  OTB Flight Disruption Tool
Day 1 operational tool for support staff to identify affected customers,
look up bookings, and export contact lists during a disruption event.

Run from otb-disruption-tool/ with:
    streamlit run ".scripts/app.py"
"""
from __future__ import annotations
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

BASE       = Path(__file__).parent.parent
BOOKINGS   = BASE / "dataFeeds" / "bookings.csv"
FLIGHTS    = BASE / "dataFeeds" / "flights.csv"
DISRUPTION = BASE / "dataFeeds" / "disruption_feed.json"

SEVERITY = {"Cancelled": 3, "Rerouted": 2, "Delayed": 1, "Scheduled": 0, "N/A": 0}

NEARBY_ORIGINS: dict[str, list[str]] = {
    "MAN": ["LBA", "LPL", "EMA"],
    "LBA": ["MAN", "LPL"],
    "LPL": ["MAN", "LBA"],
    "LGW": ["LHR", "STN", "LTN"],
    "LHR": ["LGW", "STN", "LTN"],
    "STN": ["LGW", "LHR", "LTN"],
    "LTN": ["LGW", "LHR", "STN"],
    "BHX": ["EMA", "MAN"],
    "EMA": ["BHX", "MAN"],
    "EDI": ["GLA"],
    "GLA": ["EDI"],
}

ISLAND_DESTINATIONS: set[str] = {"IBZ", "MLA", "TFS", "HER", "LCA", "CFU", "RHO", "PMI"}

UK_AIRPORTS: set[str] = {
    "MAN", "LBA", "LPL", "LGW", "LHR", "STN", "LTN",
    "BHX", "EMA", "EDI", "GLA", "BRS", "BFS", "NCL",
    "ABZ", "INV", "LCY", "SOU", "EXT", "NWI",
}

UK_AIRPORT_NAMES: dict[str, str] = {
    "MAN": "Manchester", "LBA": "Leeds Bradford", "LPL": "Liverpool",
    "LGW": "London Gatwick", "LHR": "London Heathrow",
    "STN": "London Stansted", "LTN": "London Luton",
    "BHX": "Birmingham", "EMA": "East Midlands",
    "EDI": "Edinburgh", "GLA": "Glasgow",
    "BRS": "Bristol", "BFS": "Belfast",
    "NCL": "Newcastle", "ABZ": "Aberdeen",
    "INV": "Inverness", "LCY": "London City",
    "SOU": "Southampton", "EXT": "Exeter", "NWI": "Norwich",
}

STATUS_COLOURS = {
    "Cancelled": "#c0392b",
    "Rerouted":  "#e67e22",
    "Delayed":   "#f1c40f",
    "Scheduled": "#27ae60",
    "Completed": "#5d6d7e",
    "N/A":       "#95a5a6",
}


# ---------------------------------------------------------------------------
# Data loading & enrichment
# ---------------------------------------------------------------------------

@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    bookings = pd.read_csv(BOOKINGS, dtype=str).fillna("")
    flights  = pd.read_csv(FLIGHTS,  dtype=str).fillna("")
    with open(DISRUPTION, encoding="utf-8") as f:
        feed = json.load(f)
    disruptions = {d["flight_number"]: d for d in feed["disruptions"]}
    return bookings, flights, disruptions, feed["event"]


def _effective_status(status: str, dt_str: str) -> str:
    """Return 'Completed' for past scheduled flights; all other statuses unchanged."""
    if status != "Scheduled" or not dt_str:
        return status
    try:
        if datetime.strptime(dt_str, "%Y-%m-%d %H:%M") < datetime.now():
            return "Completed"
    except ValueError:
        pass
    return status


def enrich(bookings: pd.DataFrame, disruptions: dict, iata_names: dict) -> pd.DataFrame:
    def _status(fn: str) -> str:
        if not fn:
            return "N/A"
        return disruptions[fn]["disruption_status"] if fn in disruptions else "Scheduled"

    def _reason(fn: str) -> str:
        if not fn or fn not in disruptions:
            return ""
        return disruptions[fn]["reason"]

    def _worst(ob: str, ret: str) -> str:
        candidates = [ob, ret]
        return max(candidates, key=lambda s: SEVERITY.get(s, 0))

    df = bookings.copy()
    df["outbound_status"] = df["outbound_flight_number"].apply(_status)
    df["outbound_reason"] = df["outbound_flight_number"].apply(_reason)
    df["return_status"]   = df["return_flight_number"].apply(_status)
    df["return_reason"]   = df["return_flight_number"].apply(_reason)
    df["worst_disruption"] = df.apply(
        lambda r: _worst(r["outbound_status"], r["return_status"]), axis=1
    )
    df["is_affected"] = df["worst_disruption"].isin(["Cancelled", "Rerouted", "Delayed"])
    df["outbound_origin_name"] = df["outbound_origin"].map(iata_names).fillna(df["outbound_origin"])
    # Display statuses: past scheduled flights shown as Completed
    df["outbound_display_status"] = df.apply(
        lambda r: _effective_status(r["outbound_status"], r["outbound_departure_dt"]), axis=1
    )
    df["return_display_status"] = df.apply(
        lambda r: _effective_status(r["return_status"], r["return_departure_dt"]), axis=1
    )
    return df


def status_badge(status: str) -> str:
    colour = STATUS_COLOURS.get(status, "#95a5a6")
    text_colour = "#000" if status == "Delayed" else "#fff"
    return (
        f'<span style="background:{colour};color:{text_colour};'
        f'padding:2px 8px;border-radius:4px;font-size:0.85em;font-weight:600;">'
        f"{status}</span>"
    )


# ---------------------------------------------------------------------------
# Alternatives logic
# ---------------------------------------------------------------------------

def find_alternatives(
    origin: str, destination: str, dep_dt_str: str,
    original_fn: str, flights: pd.DataFrame, disruptions: dict,
) -> dict[str, pd.DataFrame]:
    try:
        dep_date = datetime.strptime(dep_dt_str[:10], "%Y-%m-%d").date()
    except ValueError:
        empty = pd.DataFrame()
        return {"same_route": empty, "nearby_origin": empty, "other_available": empty}

    window_start = dep_date - timedelta(days=1)
    window_end   = dep_date + timedelta(days=3)
    cancelled_fns = {fn for fn, d in disruptions.items() if d["disruption_status"] == "Cancelled"}

    def _dep_date(s: str):
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

    eligible = flights[
        (flights["destination_iata"] == destination) &
        (flights["available_seats"].astype(int) > 0) &
        (~flights["flight_number"].isin(cancelled_fns)) &
        (flights["flight_number"] != original_fn)
    ].copy()
    eligible["_dep_date"] = eligible["scheduled_departure_dt"].apply(_dep_date)
    eligible = eligible[
        eligible["_dep_date"].apply(lambda d: d is not None and window_start <= d <= window_end)
    ]
    eligible["_days_diff"] = eligible["_dep_date"].apply(lambda d: abs((d - dep_date).days))
    eligible = eligible.sort_values(["_days_diff", "scheduled_departure_dt"])

    cols = ["flight_number", "airline", "origin_iata", "destination_name",
            "scheduled_departure_dt", "available_seats"]
    nearby_iatas  = NEARBY_ORIGINS.get(origin, [])
    same_route    = eligible[eligible["origin_iata"] == origin][cols].reset_index(drop=True)
    nearby_origin = eligible[eligible["origin_iata"].isin(nearby_iatas)][cols].reset_index(drop=True)
    used_fns = set(same_route["flight_number"]) | set(nearby_origin["flight_number"])
    if origin in UK_AIRPORTS:
        other_available = eligible[
            ~eligible["flight_number"].isin(used_fns) &
            eligible["origin_iata"].isin(UK_AIRPORTS)
        ][cols].reset_index(drop=True)
    else:
        other_available = pd.DataFrame(columns=cols)
    return {"same_route": same_route, "nearby_origin": nearby_origin, "other_available": other_available}


def count_alternatives(row: pd.Series, flights: pd.DataFrame, disruptions: dict) -> int:
    total = 0
    for leg, fn_col, orig_col, dest_col, dt_col in [
        ("out", "outbound_flight_number", "outbound_origin", "outbound_destination", "outbound_departure_dt"),
        ("ret", "return_flight_number",   "return_origin",   "return_destination",   "return_departure_dt"),
    ]:
        status_col = "outbound_status" if leg == "out" else "return_status"
        if row[status_col] not in ("Cancelled", "Rerouted", "Delayed"):
            continue
        r = find_alternatives(row[orig_col], row[dest_col], row[dt_col], row[fn_col], flights, disruptions)
        total += len(r["same_route"]) + len(r["nearby_origin"]) + len(r["other_available"])
    return total


def render_alternatives(row: pd.Series, flights: pd.DataFrame, disruptions: dict, iata_names: dict) -> None:
    affected_legs = []
    if row["outbound_status"] in ("Cancelled", "Rerouted", "Delayed"):
        affected_legs.append(("Outbound", row["outbound_origin"], row["outbound_destination"],
                               row["outbound_departure_dt"], row["outbound_flight_number"]))
    if row["return_status"] in ("Cancelled", "Rerouted", "Delayed"):
        affected_legs.append(("Return", row["return_origin"], row["return_destination"],
                               row["return_departure_dt"], row["return_flight_number"]))

    if not affected_legs:
        st.info("No disrupted legs to find alternatives for.")
        return

    def _apply_names(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        df["origin_iata"] = df["origin_iata"].apply(lambda c: iata_names.get(c, c))
        return df.rename(columns={
            "flight_number": "Flight", "airline": "Airline",
            "origin_iata": "From", "destination_name": "To",
            "scheduled_departure_dt": "Departure", "available_seats": "Seats Available",
        })

    for label, origin, dest, dep_dt, orig_fn in affected_legs:
        origin_name = iata_names.get(origin, origin)
        st.markdown(f"**{label} leg:** {origin_name} -> {dest}")
        results = find_alternatives(origin, dest, dep_dt, orig_fn, flights, disruptions)

        all_empty = (
            results["same_route"].empty and
            results["nearby_origin"].empty and
            results["other_available"].empty
        )
        if all_empty:
            st.warning(f"No available alternatives found for {origin_name} -> {dest} within +/-3 days.")
        else:
            if not results["same_route"].empty:
                st.markdown(f"*Same route ({origin_name} -> {dest}):*")
                st.dataframe(_apply_names(results["same_route"]),
                             width="stretch", hide_index=True)
            if not results["nearby_origin"].empty:
                nearby_labels = ", ".join(
                    iata_names.get(c, c) for c in NEARBY_ORIGINS.get(origin, [])
                )
                st.markdown(f"*Nearby airports ({nearby_labels} -> {dest}):*")
                st.dataframe(_apply_names(results["nearby_origin"]),
                             width="stretch", hide_index=True)
            if not results["other_available"].empty:
                st.markdown(f"*Other available flights to {dest} (transfer may be required):*")
                st.dataframe(_apply_names(results["other_available"]),
                             width="stretch", hide_index=True)
        if dest in ISLAND_DESTINATIONS:
            st.caption("Island destination — no nearby destination airport alternatives available.")


# ---------------------------------------------------------------------------
# Tab renderers
# ---------------------------------------------------------------------------

def tab_dashboard(df: pd.DataFrame, disruptions: dict, event: dict) -> None:
    cancelled = sum(1 for d in disruptions.values() if d["disruption_status"] == "Cancelled")
    rerouted  = sum(1 for d in disruptions.values() if d["disruption_status"] == "Rerouted")
    delayed   = sum(1 for d in disruptions.values() if d["disruption_status"] == "Delayed")

    affected = df[df["is_affected"]]
    total_pax = affected["num_passengers"].astype(int).sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Affected Bookings",    len(affected))
    c2.metric("Passengers Affected",  total_pax)
    c3.metric("Flights Cancelled",    cancelled)
    c4.metric("Flights Rerouted",     rerouted)
    c5.metric("Flights Delayed",      delayed)

    st.divider()
    st.subheader("Breakdown by destination")

    grp = (
        affected.groupby("outbound_destination_name")
        .agg(
            Bookings=("booking_ref", "count"),
            Passengers=("num_passengers", lambda x: x.astype(int).sum()),
            Cancelled=("worst_disruption", lambda x: (x == "Cancelled").sum()),
            Rerouted=("worst_disruption",  lambda x: (x == "Rerouted").sum()),
            Delayed=("worst_disruption",   lambda x: (x == "Delayed").sum()),
        )
        .reset_index()
        .rename(columns={"outbound_destination_name": "Destination"})
        .sort_values("Bookings", ascending=False)
    )
    st.dataframe(grp, width="stretch", hide_index=True)

    st.divider()
    st.subheader("Breakdown by travel status")
    grp2 = (
        affected.groupby("travel_status")
        .agg(
            Bookings=("booking_ref", "count"),
            Passengers=("num_passengers", lambda x: x.astype(int).sum()),
        )
        .reset_index()
        .rename(columns={"travel_status": "Travel Status"})
    )
    st.dataframe(grp2, width="stretch", hide_index=True)


def render_booking_card(row: pd.Series) -> None:
    is_affected = row["is_affected"]
    affected_label = (
        f'<span style="background:#c0392b;color:#fff;padding:2px 8px;border-radius:4px;'
        f'font-size:0.85em;font-weight:600;">AFFECTED</span>'
        if is_affected else
        f'<span style="background:#27ae60;color:#fff;padding:2px 8px;border-radius:4px;'
        f'font-size:0.85em;font-weight:600;">UNAFFECTED</span>'
    )
    travel_colour = {"Pre-departure": "#2980b9", "Currently Travelling": "#8e44ad", "Returned": "#7f8c8d"}
    tc = travel_colour.get(row["travel_status"], "#7f8c8d")
    travel_label = (
        f'<span style="background:{tc};color:#fff;padding:2px 8px;border-radius:4px;'
        f'font-size:0.85em;">{row["travel_status"]}</span>'
    )

    st.markdown(
        f"**{row['booking_ref']}** &nbsp; {row['lead_passenger_last_name']}, "
        f"{row['lead_passenger_first_names']} &nbsp; {travel_label} &nbsp; {affected_label}",
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    with left:
        st.markdown(f"**Hotel:** {row['hotel_name']}")
        st.markdown(f"**Passengers:** {row['num_passengers']}")
        st.markdown("**Outbound flight:**")
        st.markdown(
            f"&nbsp;&nbsp;{row['outbound_flight_number']} &nbsp; "
            f"{row['outbound_origin']} → {row['outbound_destination']} &nbsp; "
            f"{row['outbound_departure_dt']} &nbsp; "
            + status_badge(row["outbound_display_status"]),
            unsafe_allow_html=True,
        )
        if row["outbound_reason"]:
            st.markdown(f"&nbsp;&nbsp;*{row['outbound_reason']}*")
        if row["return_flight_number"]:
            st.markdown("**Return flight:**")
            st.markdown(
                f"&nbsp;&nbsp;{row['return_flight_number']} &nbsp; "
                f"{row['return_origin']} → {row['return_destination']} &nbsp; "
                f"{row['return_departure_dt']} &nbsp; "
                + status_badge(row["return_display_status"]),
                unsafe_allow_html=True,
            )
            if row["return_reason"]:
                st.markdown(f"&nbsp;&nbsp;*{row['return_reason']}*")
        else:
            st.markdown("**Return flight:** One-way booking")

    with right:
        st.markdown(f"**Email:** {row['lead_passenger_email']}")
        st.markdown(f"**Phone:** {row['lead_passenger_phone']}")
        st.markdown(f"**Booking status:** {row['booking_status']}")


def tab_lookup(df: pd.DataFrame) -> None:
    if "lookup_query" not in st.session_state:
        st.session_state["lookup_query"] = ""

    query = st.text_input(
        "Search by booking reference or passenger surname",
        placeholder="e.g. OTB-83563 or Jones",
        key="lookup_query",
    )
    if not query:
        st.info("Enter a booking reference or surname to search, or click a row in Affected Customers.")
        return

    q = query.strip().upper()
    matches = df[
        df["booking_ref"].str.upper().eq(q) |
        df["lead_passenger_last_name"].str.upper().str.contains(q, na=False)
    ]

    if matches.empty:
        st.warning(f"No bookings found for '{query}'.")
        return

    st.markdown(f"**{len(matches)} booking(s) found**")
    for _, row in matches.iterrows():
        with st.container():
            render_booking_card(row)
            st.divider()


def apply_filters(affected: pd.DataFrame, disruption_types: list, travel_status: str, leg: str) -> pd.DataFrame:
    filtered = affected.copy()
    if disruption_types:
        filtered = filtered[filtered["worst_disruption"].isin(disruption_types)]
    if travel_status != "All":
        filtered = filtered[filtered["travel_status"] == travel_status]
    if leg == "Outbound":
        filtered = filtered[filtered["outbound_status"].isin(["Cancelled", "Rerouted", "Delayed"])]
    elif leg == "Return":
        filtered = filtered[filtered["return_status"].isin(["Cancelled", "Rerouted", "Delayed"])]
    elif leg == "Both":
        ob_aff  = filtered["outbound_status"].isin(["Cancelled", "Rerouted", "Delayed"])
        ret_aff = filtered["return_status"].isin(["Cancelled", "Rerouted", "Delayed"])
        filtered = filtered[ob_aff & ret_aff]
    return filtered


def tab_affected(affected: pd.DataFrame, flights: pd.DataFrame, disruptions: dict, iata_names: dict) -> pd.DataFrame:
    fc1, fc2, fc3 = st.columns(3)
    disruption_types = fc1.multiselect(
        "Disruption type", ["Cancelled", "Rerouted", "Delayed"],
        default=[], placeholder="All types"
    )
    travel_status = fc2.selectbox(
        "Travel status", ["All", "Pre-departure", "Currently Travelling", "Returned"]
    )
    leg = fc3.selectbox("Affected leg", ["All", "Outbound", "Return", "Both"])

    filtered = apply_filters(affected, disruption_types, travel_status, leg)
    filtered = filtered.copy()
    filtered["alt_count"] = filtered.apply(
        lambda r: count_alternatives(r, flights, disruptions), axis=1
    )

    st.markdown(f"**{len(filtered)} affected booking(s) shown**")

    display_cols = {
        "booking_ref":                "Booking Ref",
        "lead_passenger_last_name":   "Surname",
        "lead_passenger_first_names": "First Name(s)",
        "num_passengers":             "Pax",
        "travel_status":              "Travel Status",
        "outbound_origin_name":       "From",
        "outbound_destination_name":  "To",
        "outbound_flight_number":       "Outbound Flight",
        "outbound_departure_dt":        "Outbound Date/Time",
        "outbound_display_status":      "Outbound Status",
        "return_flight_number":         "Return Flight",
        "return_departure_dt":          "Return Date/Time",
        "return_display_status":        "Return Status",
        "alt_count":                  "Alternatives",
        "lead_passenger_email":       "Email",
        "lead_passenger_phone":       "Phone",
    }

    table = filtered[list(display_cols.keys())].rename(columns=display_cols).reset_index(drop=True)

    selection = st.dataframe(
        table,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    if selection.selection.rows:
        idx = selection.selection.rows[0]
        row = filtered.iloc[idx]
        st.session_state["lookup_query"] = row["booking_ref"]
        st.session_state["_selected_booking"] = row["booking_ref"]

    selected_ref = st.session_state.get("_selected_booking")
    if selected_ref:
        match = filtered[filtered["booking_ref"] == selected_ref]
        if not match.empty:
            st.markdown("---")
            st.markdown(f"#### {selected_ref} — Full Booking Details")
            render_booking_card(match.iloc[0])
            with st.expander("✈️ Get Suggested Alternatives", expanded=False):
                render_alternatives(match.iloc[0], flights, disruptions, iata_names)

    return filtered


def tab_export(filtered: pd.DataFrame) -> None:
    st.markdown(
        "Download the current filtered list of affected customers as a CSV. "
        "Includes booking details, flight numbers, disruption status and reason for each leg."
    )
    st.markdown(f"**{len(filtered)} record(s) in export**")

    export_cols = [
        "booking_ref", "lead_passenger_last_name", "lead_passenger_first_names",
        "lead_passenger_email", "lead_passenger_phone", "num_passengers",
        "travel_status", "booking_status",
        "outbound_flight_number", "outbound_departure_dt", "outbound_origin",
        "outbound_destination", "outbound_status", "outbound_reason",
        "return_flight_number", "return_departure_dt", "return_origin",
        "return_destination", "return_status", "return_reason",
        "worst_disruption", "hotel_name",
    ]
    # Only include columns that actually exist in the dataframe
    export_cols = [c for c in export_cols if c in filtered.columns]
    csv = filtered[export_cols].to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇️ Download CSV",
        data=csv,
        file_name=f"otb_affected_customers_{date.today()}.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="OTB Disruption Tool", layout="wide", page_icon="✈️")
    st.title("✈️ OTB Flight Disruption Tool")

    bookings, flights, disruptions, event = load_data()
    # Build IATA → friendly name lookup; UK_AIRPORT_NAMES fills gaps for airports that only appear as origins
    iata_names = {**UK_AIRPORT_NAMES, **dict(zip(flights["destination_iata"], flights["destination_name"]))}
    df = enrich(bookings, disruptions, iata_names)
    affected = df[df["is_affected"]].copy()

    # Event banner
    st.info(
        f"**{event['title']}**  \n"
        f"{event['description']}  \n"
        f"**Disruption period:** {event['disruption_start']} to {event['disruption_end']}  \n"
        f"*Feed generated: {event['generated_at']}*"
    )

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Dashboard", "⚠️ Affected Customers", "🔍 Customer Lookup", "📥 Export"]
    )

    with tab1:
        tab_dashboard(df, disruptions, event)

    # Affected Customers runs before Customer Lookup so row-click can pre-populate the lookup query
    with tab2:
        filtered = tab_affected(affected, flights, disruptions, iata_names)
        st.session_state["filtered_df"] = filtered

    with tab3:
        tab_lookup(df)

    with tab4:
        export_df = st.session_state.get("filtered_df", affected)
        tab_export(export_df)


if __name__ == "__main__":
    main()
