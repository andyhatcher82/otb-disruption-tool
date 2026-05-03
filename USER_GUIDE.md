# OTB Flight Disruption Tool — User Guide

## Accessing the Tool

The tool is hosted online — no installation required. Simply click the link below to open it in your browser:

**[https://otb-disruption-tool.streamlit.app](https://otb-disruption-tool.streamlit.app)**

The tool loads directly in your browser. There is nothing to install.

---

## The Event Banner

At the top of every page you will see a blue information banner describing the current disruption event — the title, description, affected date range, and when the data feed was last generated. Check this to confirm you are looking at the right event.

---

## Tab 1 — Dashboard

Provides an at-a-glance summary of the disruption impact.

**Headline metrics (top row):**
- Affected Bookings — number of customer bookings with at least one disrupted flight
- Passengers Affected — total passenger count across those bookings
- Flights Cancelled — number of flights in the disruption feed with Cancelled status
- Flights Rerouted — number of Rerouted flights
- Flights Delayed — number of Delayed flights

**Breakdown by destination** — table showing how many affected bookings and passengers are travelling to each destination, with a count of cancellations, reroutes, and delays per destination.

**Breakdown by travel status** — shows how many affected customers are Pre-departure, Currently Travelling (already at their destination), or Returned.

---

## Tab 2 — Affected Customers

The main working view. Shows all customers with at least one disrupted flight.

### Filters

Use the three dropdowns at the top to narrow the list:

- **Disruption type** — filter to Cancelled, Rerouted, or Delayed (select multiple). Leave blank to show all.
- **Travel status** — filter to Pre-departure, Currently Travelling, or Returned. Default shows all.
- **Affected leg** — filter to customers where only the Outbound is affected, only the Return, both, or all.

The count above the table updates to reflect how many bookings match your filters. The **Alternatives** column shows at a glance how many replacement flight options are available for each booking.

### Selecting a booking

Click the checkbox in a row to select that booking. A full booking card will appear below the table showing:

- Passenger name, booking reference, travel status, and affected/unaffected badge
- Hotel name and passenger count
- Outbound flight: flight number, route, departure date/time, and status badge
- Return flight: same details (or "One-way booking" if applicable)
- Disruption reason for each affected leg
- Contact details: email address and phone number

### Getting suggested alternatives

With a booking selected, click **Get Suggested Alternatives** to expand the alternatives panel.

For each affected leg, the tool searches for available flights (seats > 0, not themselves cancelled) departing within 1 day before to 3 days after the original departure date. Results are grouped into:

- **Same route** — flights from the same departure airport to the same destination
- **Nearby airports** — flights from nearby UK airports (within ~2hr drive) to the same destination
- **Other available flights** — other UK-departure flights to the same destination where a transfer to a different airport may be needed

Results are sorted with the closest date to the original departure first.

Note: For island destinations (Ibiza, Malta, Tenerife, Rhodes, Corfu, Cyprus, Crete, Majorca) no nearby destination alternatives are shown — there are no road connections between island airports and mainland airports.

If no alternatives are available, a warning is shown.

---

## Tab 3 — Customer Lookup

Search for any booking — affected or unaffected — by booking reference or passenger surname.

Type in the search box and press Enter. Results appear immediately. The search is case-insensitive.

- **By booking reference:** enter the full reference, e.g. `OTB-83563`
- **By surname:** enter any part of the surname, e.g. `jones` — all matching bookings will be shown

Each result shows a full booking card (same format as Affected Customers).

**Tip:** Clicking a row in the Affected Customers tab automatically populates the search box here so you can navigate between tabs without re-typing.

---

## Tab 4 — Export

Download the current filtered list of affected customers as a CSV file.

The export reflects whatever filters are currently active on the Affected Customers tab. To export all affected customers, clear all filters first.

Click **Download CSV**. The file is named `otb_affected_customers_YYYY-MM-DD.csv` and includes:

- Booking reference, passenger name, email, phone, passenger count
- Travel status and booking status
- Outbound and return flight numbers, departure times, origins, destinations
- Disruption status and reason for each leg
- Hotel name

This file can be handed to the comms team for email or push notification outreach.

---

## Status Badges

| Badge | Meaning |
|---|---|
| Red — Cancelled | Flight has been cancelled. Customer needs rebooking. |
| Orange — Rerouted | Flight is operating but via a different route. Arrival time may be affected. |
| Yellow — Delayed | Flight is operating but departure is delayed. |
| Green — Scheduled | Flight is operating normally. |
| Grey — Completed | Flight has already departed (past flights shown as Completed). |
| Light grey — N/A | No return flight (one-way booking). |

---

## Running Locally (optional)

If you need to run the tool locally — for example, to connect to a different data feed — you will need Python 3.10+ and the packages listed in `requirements.txt`.

```
pip install -r requirements.txt
python -m streamlit run ".scripts/app.py"
```

Then open `http://localhost:8501` in your browser.
