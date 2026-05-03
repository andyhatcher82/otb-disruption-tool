# OTB Flight Disruption Tool — Solution Summary

## Scenario

A French ATC strike has restricted French airspace to ~50% capacity, affecting UK holiday flights between 2 May and 8 May 2026. Flights landing in France are largely unaffected (90% still operate). Through-France flights face significant disruption: approximately 30% cancelled and 20% rerouted. An additional 5 operational cancellations (mechanical faults and crew hour limits) are also present. The support team needs a fast, accurate way to identify which customers are affected, look up individual bookings, find alternatives, and export contact lists for outreach.

---

## What Was Built

### Day 1 Deliverable: Three mock data files + one Streamlit app

| File | Description |
|---|---|
| `dataFeeds/bookings.csv` | 200 customer bookings across 15+ origins and 30+ destinations |
| `dataFeeds/flights.csv` | 2,500 scheduled flights covering the disruption window and surrounding weeks |
| `dataFeeds/disruption_feed.json` | 146 disruption records for the 2 May–8 May window |
| `.scripts/app.py` | Streamlit operational tool — 4 tabs, runs locally in a browser |

### App Tabs

**Dashboard** — live event banner, 5 headline metrics (affected bookings, passengers, cancellations, reroutes, delays), breakdown tables by destination and travel status.

**Affected Customers** — filterable table of all disrupted bookings (filter by disruption type, travel status, affected leg). Clicking a row expands a full booking card with contact details, flight statuses, and a "Get Suggested Alternatives" expander showing available replacement flights sorted by proximity to the original departure date.

**Customer Lookup** — search any booking by reference number or passenger surname; returns full booking cards for affected and unaffected customers alike. Clicking a row in Affected Customers pre-populates this tab.

**Export** — one-click CSV download of the current filtered affected customer list, including flight details, disruption reasons, and contact information.

---

## Architecture Decisions

**Single-file Streamlit app** — all app logic lives in `.scripts/app.py`. No database, no API layer, no authentication. Deliberately simple: support staff open a URL, the tool loads. No deployment complexity for Day 1.

**Pandas for data joins** — bookings and disruptions are joined in memory at load time using `@st.cache_data`. With 200 bookings the overhead is negligible. The enrichment step adds derived columns (`outbound_status`, `return_status`, `worst_disruption`, `is_affected`, display status) so the rest of the app can filter and render without recomputing.

**Mock disruption feed as JSON** — the feed is a flat list of disrupted flight numbers with status and reason. The app treats any flight number absent from the feed as "Scheduled". This mirrors how a real webhook payload would be structured, making the integration path clear for Day 2.

**Pipe-delimited `route_via` field** — each flight stores its overflown countries as `England|France|Spain|Portugal`. The disruption generator classifies flights by checking whether "France" appears in this list. Rerouted flights replace France with an Atlantic or Germany corridor. This avoids geospatial computation while being accurate enough for the scenario.

**`_effective_status()` helper** — flights with a past departure date and no disruption are displayed as "Completed" rather than "Scheduled", giving support staff a cleaner picture without modifying the underlying data.

**Alternatives search** — `find_alternatives()` queries flights.csv for same-route and nearby-origin flights within ±3 days of the disrupted departure, excluding cancelled flights. UK airport clusters are hardcoded (`NEARBY_ORIGINS`). Non-UK origin bookings (e.g. AMS, BCN) only return same-airport alternatives — suggesting UK airports to a customer in Amsterdam is not helpful.

---

## Key Assumptions

- The disruption feed is consumed as a full snapshot (not a delta). All flights absent from the feed are assumed Scheduled.
- "Currently Travelling" means the customer's outbound flight has departed but their return has not yet departed (i.e. they are at the destination).
- Alternative flights with `available_seats = 0` are excluded. In a live system, seat availability would be queried in real time.
- Island destinations (Ibiza, Malta, Tenerife, Rhodes, etc.) have no road-accessible nearby destination alternatives. Only same-airport alternatives are shown.
- UK nearby airport clusters are defined by ~2hr drive time. Clusters: London (LGW/LHR/STN/LTN), Manchester/Yorkshire (MAN/LBA/LPL), Midlands (BHX/EMA), Scotland (EDI/GLA).
- The mock data uses August 2026 as the booking date range to reflect a realistic peak season load.

---

## Trade-offs

| Decision | Why | What it costs |
|---|---|---|
| Static JSON feed rather than live webhook | No infrastructure needed for Day 1; fast to build and test | Feed must be manually refreshed; does not reflect real-time changes |
| In-memory data joins (no DB) | Zero setup, no connection strings, portable | Does not scale beyond ~10,000 bookings before slowdown |
| available_seats in flights.csv (not a live API) | Allows alternatives feature to work on Day 1 | Seat counts go stale immediately; customers may arrive at the airport to find a "full" flight |
| Single support URL, no authentication | Fast deployment, no IT dependency | Any person with the URL can see all customer data |

---

## What Would Be Improved

1. **Replace mock feed with live webhook** — see Day 2 Scope. The JSON structure is already designed to be a drop-in replacement.
2. **Real-time seat availability** — call the airline GDS/NDC API when alternatives are requested, rather than using a stale static value.
3. **Batch comms** — email and push notification to affected customers directing them to self-serve rebooking. Requires Ops and Marketing sign-off before any send.
4. **Self-serve rebooking** — deep-link from the comms into the OTB app, pre-populated with alternatives, to reduce inbound call volume.
5. **Authentication** — even basic SSO would prevent customer data being exposed to unauthorised users.
6. **Audit log** — record which support agent viewed or exported which booking, for GDPR compliance.
