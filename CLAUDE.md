# CLAUDE.md — OTB Flight Disruption Tool

Instructions for AI assistants working on this repository.

---

## Project Overview

A Streamlit-based operational tool for support staff to manage flight disruptions. Mock data simulates a French ATC strike (2 May–8 May 2026). The tool identifies affected customers, surfaces alternative flights, and exports contact lists.

---

## Folder Structure — Non-Negotiable

```
otb-disruption-tool/
├── .scripts/          Python scripts ONLY (app.py, generate_*.py)
├── dataFeeds/         All CSV and JSON data files ONLY
├── requirements.txt   Python dependencies (repo root)
├── CLAUDE.md          This file
├── USER_GUIDE.md      End-user documentation
├── SOLUTION_SUMMARY.md  Architecture and decisions
└── DAY2_SCOPE.md      Future roadmap
```

Never put data files in `.scripts/` and never put Python scripts in `dataFeeds/`.

---

## Time Log

Every piece of work — however small — must be logged in `time_log.md` at the repo root (outside `otb-disruption-tool/`).

**Rules:**
- Get the real system clock time before starting any work. Never approximate or guess.
- Write a **start entry** before doing anything — including before entering plan mode.
- Write a **close entry** as the very last action when the work is complete.
- Every task, however small (even 1-minute tweaks), gets its own log entry.
- Andy writes his own entries manually. Do not write entries on his behalf.

**Format:**
```
| # | Date | From | To | Duration | Who | Activity |
```

---

## Before Writing Any Code

For any non-trivial change, enter plan mode first. Present the plan for approval before touching files. Do not implement and explain simultaneously — plan first, implement after approval.

---

## Python Style

- No comments unless the reason is genuinely non-obvious to a reader.
- No docstrings beyond a single short line.
- No error handling for scenarios that cannot happen — trust internal logic.
- Validate only at system boundaries (user input, external file reads).
- No unused variables, no backwards-compatibility shims.
- All data files read with `encoding="utf-8"` explicitly.
- File paths always via `pathlib.Path`, never hardcoded strings.

---

## Streamlit Conventions

- Use `width="stretch"` not `use_container_width=True` (deprecated, removed after 2025-12-31).
- Use `@st.cache_data` for all data loading functions.
- Cross-tab state via `st.session_state` with explicit key names.
- All data loaded as `dtype=str` and `.fillna("")` — no silent type coercion.
- Restart the app and confirm clean startup (no errors, no warnings) after every change.

---

## Data Generation Scripts

- `generate_bookings.py` and `generate_flights.py` use a fixed `SEED` — do not change it without regenerating all downstream files.
- After any change to `generate_flights.py`, always regenerate `disruption_feed.json` immediately (`python .scripts/generate_disruption_feed.py`).
- After regenerating `flights.csv`, verify: "Verification passed: all N booked flights present in flights.csv".
- `TARGET_FLIGHTS = 2500` — do not reduce this without discussion.

---

## Flight Data Rules

- `route_via` is a pipe-delimited country list (e.g. `England|France|Spain|Portugal`).
- `SOUTHERN_ORIGINS = {"BCN", "FCO"}` — these airports are south of France; France must never appear in their `route_via`.
- Disruption classification: `via_france` = France in route_via; `lands_france` = destination in `{"NCE","CDG","LYS","MRS"}`; `unaffected` = neither.
- `available_seats` is 0–12% of `total_capacity` (August peak, 88–100% full).

---

## Alternatives Feature Rules

- **`UK_AIRPORTS`** — only these airports are valid for `nearby_origin` and `other_available` suggestions.
- **`NEARBY_ORIGINS`** — UK airport clusters within ~2hr drive. Do not add airports more than 2hr apart.
- **`ISLAND_DESTINATIONS`** = `{"IBZ","MLA","TFS","HER","LCA","CFU","RHO","PMI"}` — no nearby destination alternatives for these.
- **Non-UK origins** (AMS, BCN, FCO, etc.) — return empty `other_available`. Never suggest UK airports to a customer whose origin is not in the UK.
- Alternatives search window: departure date −1 day to +3 days.
- Exclude flights that are themselves cancelled from alternatives.
- Sort results by `abs(candidate_date − original_date)` ascending, then by departure time.

---

## Communications (Day 2)

No batch emails or push notifications may be sent without explicit sign-off from both Operations and Marketing. Do not build automated send functionality without this gate in place.

---

## What Not to Do

- Do not add features, refactor, or introduce abstractions beyond what the task explicitly requires.
- Do not add fallback handling for scenarios that cannot occur.
- Do not create new documentation files (`*.md`) unless explicitly asked.
- Do not commit changes unless explicitly asked.
- Do not push to the remote repository unless explicitly asked.
- Do not approximate timestamps in the time log — always check the system clock.
