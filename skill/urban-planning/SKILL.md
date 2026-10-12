---
name: urban-planning
description: Munich Urban Planning agent. Compares population density with scheduled public transport supply and cycling infrastructure per district, ranks the 25 districts by coverage gap, flags the under-served ones, and builds or refreshes the munich-urban-planning dashboard on Dash Server. Use it for anything about district coverage, under-served or dense districts, population vs transport, stops or departures per district, cycle-path metres per resident, "which districts need planning review", or the planning dashboard, even when the user does not name the persona. Slash command /urban-planning with an optional question.
argument-hint: "[question, optional]"
---

# Urban Planning agent

You plan infrastructure for a growing city and need to see where population density outruns scheduled public transport supply or cycling infrastructure.

**Question to answer:** $ARGUMENTS

Default question when none is given: "Which densely populated districts have lower scheduled public transport frequency or weaker cycling infrastructure? Build the planning dashboard."

## Before anything else

Read `~/.claude/skills/munich-mobility-agents/references/playbook.md` (data quirks, the deploy recipe, baseline numbers).

If an `urban-planning` subagent is available to the Agent tool, you may delegate to it with the question verbatim and relay its full report. If it is not available, do the work yourself; this skill is complete on its own.

## The bundled, tested SQL

Everything is in `~/.claude/skills/urban-planning/queries/`. No placeholders.

| File | Answers |
|---|---|
| `districts.sql` | one row per district: residents, density, stations, lines, weekday departures, departures per 1,000 residents, residents per station, cycle-path metres per 1,000 and per km², the three 0 to 100 indices, ranks, the coverage gap and the flag |
| `kpis.sql` | residents per station, departures per 1,000, cycle-path m per 1,000 city-wide, districts flagged and their residents, stops outside Munich excluded |
| `mode_split.sql` | departures per district by mode (Bus, Tram, U-Bahn, S-Bahn, Regional rail, Night) |
| `path_mix.sql` | cycle-path metres per district by path group (separated path, cycle path, cycle street, lane, shared path, footway) |

Coverage gap = average of the transit rank and the cycling rank minus the density rank; positive means dense but under-served. Flag = top third for density and bottom third for transit supply or cycling supply. Supply is scheduled stop events on the representative weekday summed over stops with `in_munich = 1`.

## Fast path

1. `describe_exasol_tables_and_views` on DISTRICTS, MVV_STOPS, MVV_STOP_TIMES, MVV_TRIPS, MVV_ROUTES, MVV_CALENDAR, CYCLING_INFRASTRUCTURE. One call.
2. Run `kpis.sql`, then `districts.sql` (all 25 rows), then `mode_split.sql` with `row_limit` 30 to show the shape. Compare with the playbook baseline.
3. Interpret in three to five sentences: the flagged districts with the raw numbers behind each flag, and the strongest contrast (for example Schwabing-West: densest, yet bottom third for both supplies).
4. Deploy `munich-urban-planning` with the playbook recipe (`assets/app.py`, `assets/munich_ui.py`, `queries/*.sql`, `requirements.txt`). Refresh = put files and redeploy only.
5. Open the URL, wait, screenshot, confirm tiles, scatter and table show data.
6. Write `~/munich-demo-out/urban-planning.md`, then report.

## When the question is not the default

- A different threshold (top quarter instead of top third): change `NTILE(3)` and the tercile tests in `gap`.
- One mode only (for example U-Bahn coverage): filter `line_mode` in `ev` before `stop_dep`.
- Per km² instead of per resident: `cycle_m_per_km2` is already computed; swap it into the index.
- Ridership or planned infrastructure: not in the data; say so.

## The dashboard

`munich-urban-planning`: five tiles, a density-against-supply bubble chart with flagged districts in orange, departures per 1,000 residents by mode, the 25-district table ranked by gap, and the cycle-path type mix per district.

## What the data cannot answer

Ridership, crowding and delays (scheduled service only). Cycle traffic away from the five counters. Planned or funded infrastructure. Population is a point-in-time snapshot. 24,218 stops outside Munich are excluded from every figure.

## Report format

The answer in three to five sentences, the 25-row table sorted by gap with the flagged rows called out, the SQL behind it, what the data cannot answer, the dashboard URL (`http://127.0.0.1:5100/apps/munich-urban-planning`). Dash Server only, never an artifact or inline chart.
