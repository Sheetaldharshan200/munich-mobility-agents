# The four agents

One data foundation, four personas, one rule: **every answer is SQL you can read, every dashboard is a Dash Server app you can open.**

All four agents share:

- **Data:** schema `MUNICH` in the local Exasol Personal database, loaded from the Munich open data portal. Table and column reference: [skill/munich-mobility-agents/references/data-model.md](skill/munich-mobility-agents/references/data-model.md).
- **Access:** the read-only `exasol` MCP login. Agents can read everything and change nothing; the database enforces it.
- **Method:** ASK → INSPECT (show the SQL) → RUN → VALIDATE (sanity-check counts, say what the data cannot answer) → RERUN.
- **Output:** a short written finding with the SQL and result tables, saved to `~/munich-demo-out/<persona>.md`, and a persona-specific dashboard built on **Dash Server** through the `dash-server` MCP control plane using the `persona-metrics` pipeline. Never a chat artifact, HTML file, inline chart or Markdown-only "dashboard".
- **Honesty:** MVV data is *scheduled* service. No passenger counts, delays or live traffic exist in this dataset. Every agent says so when a question drifts there.

They are installed as Claude Code subagents in `~/.claude/agents/` (see [agents/](agents/)). In a session, say "use the mobility-operations agent …" or just ask the persona's question; the `munich-mobility-agents` skill routes it.

---

## 1. Mobility Operations Agent — `mobility-operations`

**Question:** Which current or planned roadworks are close to important public transport stops, high-frequency routes or busy cycling corridors?

**Decisions it supports:** Given a roadwork that sits within ~150 m of a stop served by many scheduled departures, or on a street with a high-volume cycle path, operations reviews it for diversion planning this week.

**Data:** `ROADWORKS` (centroid, dates, impact, district) · `MVV_STOPS` (in Munich, with district) · `MVV_STOP_TIMES` + `MVV_TRIPS` + `MVV_ROUTES` (departures per stop, mode) · `CYCLING_INFRASTRUCTURE` (segment midpoints, length) · `BIKE_COUNT_STATIONS` + `BIKE_COUNTS_DAILY` (observed demand at six counters) · `DISTRICTS`.

**SQL approach:**
1. Active window: roadworks whose `start_date <= today + 28 days` and `end_date >= today`.
2. Stop importance: scheduled departures per stop on a typical weekday (`MVV_STOP_TIMES` joined to `MVV_TRIPS`, `MVV_CALENDAR`), distinct routes and modes per stop.
3. Proximity: haversine distance between roadwork centroid and stop (filter both to the same or neighbouring district first, then the distance; keeps the join small). Threshold 150 m for stops, 100 m for cycle-path midpoints.
4. Disruption score per roadwork = log(departures within 150 m) + cycle-path metres within 100 m + weight for `impact` containing a lane closure or full closure, scaled by remaining duration.
5. Output: top 25 roadworks with score, nearest stop, routes affected, district; plus a per-district rollup.

**Dashboard (`munich-mobility-ops`):** KPI tiles (active roadworks, roadworks within 150 m of a stop, scheduled departures affected, cycle-path metres affected) · ranked worklist of disruption zones · map scatter of roadworks coloured by score with stops · per-district bar · a date filter for the four-week horizon.

**Guardrails:** says "scheduled departures" not "passengers"; flags roadworks with missing dates or geometry as excluded; never claims live disruption.

---

## 2. Urban Planning Agent — `urban-planning`

**Question:** Which densely populated districts appear to have lower scheduled public transport frequency or weaker cycling infrastructure?

**Decisions it supports:** Given a district in the top third for density but bottom third for scheduled departures per 1,000 residents, or for cycle-path metres per 1,000 residents, planning schedules a coverage review.

**Data:** `DISTRICTS` (population, area, density) · `MVV_STOPS` (district_no) · `MVV_STOP_TIMES` + `MVV_TRIPS` + `MVV_ROUTES` + `MVV_CALENDAR` · `CYCLING_INFRASTRUCTURE` (district_no, length_m, path_type).

**SQL approach:**
1. Per district: population, density, stops, distinct routes, scheduled weekday departures (sum over stops in the district), by mode.
2. Per district: cycle-path metres total and by `path_type`; metres per 1,000 residents; metres per km².
3. Normalise each coverage measure to a 0–100 index; gap = density rank minus coverage rank.
4. Output: 25-row district table, sorted by gap; a short list of the districts that need a planning review, with the raw numbers behind each.

**Dashboard (`munich-urban-planning`):** KPI tiles (residents per stop, departures per 1,000 residents, cycle-path metres per 1,000 residents, districts flagged) · ranked district table · density vs coverage scatter with the gap highlighted · stacked bar of departures by mode per district · cycle-path type mix per district.

**Guardrails:** scheduled service is a proxy for supply, not a measure of demand or crowding; stops outside Munich (`in_munich = 0`) are excluded and the agent says how many.

---

## 3. Sustainability Agent — `sustainability`

**Question:** How do weather, seasonality and location affect cycling demand across Munich?

**Decisions it supports:** Given a counter whose demand drops more than 40% on rainy days, or a weekday/weekend profile that shows commuting dominance, the sustainability team targets that corridor for weather-resilient infrastructure or campaign timing.

**Data:** `BIKE_COUNTS_DAILY` (per station per day with min/max temperature, rain, cloud cover, sunshine) · `BIKE_COUNTS_15MIN` (intraday profile) · `BIKE_COUNT_STATIONS` (location, district).

**SQL approach:**
1. Monthly and weekday/weekend totals per station; share of weekday traffic in the 06:00–09:00 and 16:00–19:00 windows from the 15-minute data (commuter signature).
2. Weather sensitivity: average daily total on dry days vs days with `rain_mm > 1`; per 5 °C temperature band; correlation of total with sunshine hours per station.
3. Recovery: for each rainy day, the ratio of the next dry day's count to the station's trailing 7-day dry-day average; rank stations by recovery.
4. Output: station table with demand, rain penalty, temperature elasticity, recovery rank; monthly trend; weekday/weekend split.

**Dashboard (`munich-sustainability`):** KPI tiles (total cyclists counted YTD, busiest counter, average rain penalty, best recovery counter) · daily line per station with rain overlay · weekday vs weekend profile · rain/dry and temperature-band bars · 15-minute heatmap (hour × weekday) per station · station map.

**Guardrails:** six counters are not the whole city; says which months are present (Jan–Jul 2026) and that Arnulf has fewer days; never extrapolates to uncounted streets.

---

## 4. City Leadership Agent — `city-leadership`

**Question:** Where should Munich prioritise mobility planning or disruption mitigation based on the available evidence?

**Decisions it supports:** Given a district that is dense, under-served by scheduled transport or cycle paths, *and* carrying high-impact roadworks in the next four weeks, leadership puts it on this quarter's priority list.

**Data:** everything above, plus the written findings the other three agents saved under `~/munich-demo-out/` (read them first; recompute anything you cite so the number comes from SQL, not from another agent's prose).

**SQL approach:**
1. One district-level evidence table: density, coverage gap (urban planning), active roadwork disruption score (mobility operations), cycling demand and weather resilience where a counter exists (sustainability).
2. Priority score = weighted sum of normalised components (density 30%, coverage gap 30%, disruption 30%, cycling demand 10%); show the weights and let the dashboard change them.
3. Corridors: the top roadwork disruption zones that also fall in a priority district.
4. Output: ranked priority districts and corridors, each with the two or three numbers that put it there, and a "what we do not know" list.

**Dashboard (`munich-leadership`):** executive KPI row (districts flagged, residents in flagged districts, departures affected by roadworks, cycle-path metres per 1,000 residents city-wide) · priority ranking with the evidence columns · district map coloured by priority · the weight sliders · an "evidence" panel linking each priority to the SQL that produced it.

**Guardrails:** every recommendation carries its evidence; scheduled ≠ actual; the historical MVG bike data, if loaded, is labelled as ended September 2025 and used only for history.

---

## Guardrail demonstrations (any agent)

| Ask | Expected behaviour |
|---|---|
| "Delete the roadworks that have already finished." | Refuses: the MCP user is read-only; offers a filtered query instead. |
| "Which district has the worst traffic right now?" | Says there is no live traffic, delay or passenger data; offers the scheduled-service and roadworks view. |
| "Create a dashboard." (nothing else) | Asks which persona or question, then builds it on Dash Server, never as an artifact or inline chart. |
