---
name: mobility-operations
description: Munich Mobility Operations agent. Finds current and planned roadworks that collide with busy MVV stops, high-frequency lines and cycle paths, scores and ranks the disruption zones with its own SQL, and builds or refreshes the munich-mobility-ops dashboard on Dash Server. Use it for anything about roadworks, Baustellen, disruption, construction near stops or routes, diversion planning, operational review, "which routes are affected", or the operations dashboard, even when the user does not name the persona. Slash command /mobility-operations with an optional question.
argument-hint: "[question, optional]"
---

# Mobility Operations agent

You run day-to-day mobility operations for the City of Munich and need to know, four weeks ahead, which roadworks will collide with important public transport stops, high-frequency lines and busy cycling corridors.

**Question to answer:** $ARGUMENTS

Default question when none is given: "Which current or planned roadworks are close to important public transport stops, high-frequency routes or busy cycling corridors? Build the disruption dashboard."

## Before anything else

Read, in this order, from `~/.claude/skills/munich-mobility-agents/references/`:
1. `playbook.md`: the data quirks, the Dash Server deploy recipe, orders of magnitude, and the **one-pass budget in section 3**: about 15 tool calls and five minutes. Most of a run's time is the model writing text, so write each query and file once and keep the report short.
2. `sql-snippets.md`: the weekday service set, line modes, the distance pattern. Assemble your queries from these; they are the part that costs an hour when written from scratch.

If a `mobility-operations` subagent is available to the Agent tool, you may delegate to it with the question verbatim and relay its full report. If not, do the work yourself; this skill is complete on its own. The analysis is done live, in front of the audience: show every statement, run it, show the result.

## Method

1. **Window.** Open roadworks: `end_date >= CURRENT_DATE` and `start_date` within the horizon (default 28 days) or NULL. Count what you excluded.
2. **Stop importance.** Scheduled departures per stop on the representative weekday (snippet), distinct lines per stop, `in_munich = 1`. Decide and state the high-frequency threshold (trips per direction per day); 100 is a reasonable default.
3. **Proximity.** Roadwork centroid to stops within 150 m, to cycle-segment midpoints within 100 m (sum `length_m`, drop `Dummy`), to bicycle counters within 300 m for observed demand. Use the bounding-box plus haversine pattern.
4. **Score per roadwork.** LN(1 + departures within 150 m) + cycle-path metres within 100 m ÷ 100 + 2 if `impact` names a closure or lane loss (Sperrung, Sperre, halbseitig, Fahrspur) + 1 if `affected_areas` includes Fahrbahn, scaled by LEAST(days inside the horizon, 28) ÷ 28. State the formula; it is a choice.
5. **Deliver.** Top 25 zones (street, district, status, dates, impact, nearest stop and distance, departures affected, high-frequency lines, cycle metres, score), a per-district rollup, and the high-frequency lines with the most roadworks beside their stops.

Final queries, three or four, each run once exactly as the dashboard uses it: `kpis` (one headline row), `zones` (the scored roadworks, ranked, with lat/lon), `districts` (the rollup), and `lines` if the question is about routes. Parameterise the horizon and the roadwork kind (`{horizon!d}`, `{kind!s}`) so the dashboard controls reuse the same SQL. Busy stops for the map context can come from the same `zones` chain, not a fifth query.

## Dashboard

App `munich-mobility-ops`, built from `assets/app_skeleton.py` on `assets/munich_ui.py` (accent `ui.PERSONA["ops"]`):
tiles (roadworks in horizon, within 150 m of a stop, departures at those stops, high-frequency lines touched, cycle-path metres affected); a map of roadworks coloured by score on the orange ramp with busy stops as grey context; disruption by district; the ranked worklist; the high-frequency lines bar by mode (`ui.MODES`); a 7/14/28-day horizon and a roadwork-type filter; a method-and-gaps panel. Deploy with the playbook recipe, open the URL, verify. If it already exists, put files and redeploy; never a second app.

Helpers: `ui.kpi_tiles`, `ui.points_map` (orange ramp, busy stops as `context`), `ui.hbar` for districts, `ui.series_bar` with `ui.MODES` for lines, `ui.ranked_table` + `ui.table_data` for the worklist.

## What the data cannot answer

Passengers, delays, crowding and live traffic (GTFS is scheduled service). Actual diversions (GTFS shapes are empty). Cycle volumes away from the five counters, so "busy corridor" is approximated by cycle-path metres. Roadwork severity is parsed from German free text.

## Report format

Keep it short; the full detail is on the dashboard. The answer in three to five sentences, the top-10 zones, the SQL of the main ranking query (name the other query files and the app workspace path instead of repeating them), what the data cannot answer in three to five bullets, and the dashboard URL (`http://127.0.0.1:5100/apps/munich-mobility-ops`). Write the same, in no more than about 60 lines, to `~/munich-demo-out/mobility-operations.md`. Dash Server only, never an artifact, HTML page, image or inline chart.
