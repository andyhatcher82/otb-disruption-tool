# OTB Flight Disruption Tool — Day 2 Scope

Day 1 delivered a functional operational tool running on mock data. Day 2 replaces the static mock layer with live data feeds, adds outbound customer communications, and opens the path to self-serve rebooking — materially reducing inbound contact volume during disruption events.

---

## 1. Live Disruption Feed (Webhook)

**Day 1:** `disruption_feed.json` is a static snapshot, manually regenerated.

**Day 2:** Replace with a real-time webhook endpoint that pushes disruption updates as they are confirmed by airlines and ATC. The app switches from reading a file to polling or subscribing to the feed.

**Changes required:**
- Stand up a lightweight API endpoint (or subscribe to an existing airline data feed / aggregator such as Cirium or FlightAware).
- App `load_data()` fetches the feed via HTTP rather than reading from disk. Feed schema is already compatible — same JSON structure.
- Add a "Last updated" timestamp and a manual refresh button in the event banner so support staff know when the data was last pulled.
- Consider a background refresh interval (e.g. every 5 minutes) using Streamlit's `st.rerun` with a timer, or move to a server-side job that writes the feed to a shared store.

**Risk:** Webhook reliability during the disruption event itself (high traffic periods). Implement a fallback to the last-known-good snapshot if the feed is unreachable.

---

## 2. Real-Time Seat Availability API

**Day 1:** `available_seats` is a static field in `flights.csv`, computed at generation time and immediately stale.

**Day 2:** When a support agent opens the "Get Suggested Alternatives" expander, trigger a live API call to the airline GDS or OTB's own inventory system to fetch current seat availability for each candidate flight.

**Changes required:**
- Add a `get_live_seat_availability(flight_numbers: list[str]) -> dict[str, int]` function that calls the relevant API.
- Cache responses for 60–90 seconds per flight (using `st.cache_data(ttl=90)`) to avoid hammering the API when multiple agents are viewing the same booking.
- Display a loading spinner while the call resolves.
- Fall back to the static `available_seats` value with a "live data unavailable" notice if the API is unreachable.

**Risk:** API rate limits during peak disruption. Batch the request for all candidate flight numbers in a single call where the API supports it.

---

## 3. Nearby Destination Airport Alternatives

**Day 1:** Nearby origin alternatives are shown (UK airport clusters). No nearby destination alternatives are suggested — the destination airport list is static.

**Day 2:** For mainland destinations where a road transfer is practical, suggest flights to nearby airports at the destination end (e.g. AGP/MJV for Malaga area, LIS as an alternative to FAO for the Algarve). Island destinations remain excluded (IBZ, MLA, TFS, RHO, HER, LCA, CFU, PMI).

**Changes required:**
- Define a `NEARBY_DESTINATIONS` dict (destination IATA → list of nearby destination IATAs) mirroring the existing `NEARBY_ORIGINS` pattern.
- Update `find_alternatives()` to query the additional destination IATAs and return a fourth bucket: `nearby_destination`.
- Surface in the alternatives expander under a "Nearby destination airports" section with a transfer distance/time note.
- Populate `flights.csv` (or the live feed) with flights to the additional destination IATAs.

---

## 4. Batch Customer Communications

**Day 1:** No comms capability. Export tab provides a CSV for manual handoff.

**Day 2:** Support or Operations staff can trigger a batch email and/or push notification to all affected customers from within the tool.

**Sign-off requirement:** All comms templates must be reviewed and approved by Operations and Marketing before any send is possible. No automated sends without explicit sign-off. The tool should enforce this with a workflow state (Draft → Approved → Sent) rather than relying on process alone.

**Changes required:**
- Add a "Send Communications" tab (or expand Export).
- Template editor: pre-populated subject and body with merge fields (`{{first_name}}`, `{{booking_ref}}`, `{{outbound_flight}}`, `{{disruption_reason}}`). Separate templates for Cancelled, Rerouted, Delayed.
- Approval workflow: "Submit for approval" button generates a preview and sends an approval request to a nominated Ops/Marketing contact. Only approved templates can be sent.
- Integration with OTB email send platform and iOS/Android push notification service.
- Comms log: record which customers were contacted, when, and via which channel — critical for GDPR accountability and to prevent duplicate sends.
- Opt-out check: suppress sends for customers who have opted out of marketing/operational communications.

**Risk:** Sending incorrect or premature comms during a fast-moving disruption event can damage customer trust and increase inbound volume. The approval gate is non-negotiable.

---

## 5. Self-Serve Rebooking

**Day 1:** Alternatives are surfaced to support staff only.

**Day 2:** Customer comms deep-link directly into the OTB app or web booking flow, pre-populated with their booking reference and the available alternative flights identified by the disruption tool. Customers can confirm a rebooking without calling.

**Changes required:**
- Generate a personalised, time-limited deep-link per customer (e.g. `otb.com/rebook?ref=OTB-83563&token=xxx`) included in the comms.
- OTB app/web receives the token, authenticates the customer, presents the pre-filtered alternatives, and allows one-click rebooking.
- Disruption tool dashboard gains a "Self-served" metric: bookings where the customer completed rebooking without agent intervention.
- Suppresses the booking from the "still unresolved" view in the tool once a customer has self-served.

**Dependency:** Requires integration with OTB booking engine and app deep-link infrastructure. Not a standalone Streamlit change — needs engineering team involvement.

---

## Priority Order

| Priority | Item | Effort | Impact |
|---|---|---|---|
| 1 | Live disruption feed | Low–Medium | High — removes need to manually refresh data |
| 2 | Batch comms (with approval gate) | Medium | Very High — proactive contact reduces inbound call volume |
| 3 | Real-time seat availability | Medium | High — prevents agents suggesting genuinely full flights |
| 4 | Self-serve rebooking | High | Very High — eliminates call for straightforward rebookings |
| 5 | Nearby destination alternatives | Low | Medium — incremental improvement to alternatives quality |
