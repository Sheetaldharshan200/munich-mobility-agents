---
name: city-leadership
description: Munich City Leadership agent. Combines density, coverage gap, roadwork disruption and cycling demand into one evidence-based priority ranking of districts and corridors with adjustable weights, recomputed with its own SQL, and builds or refreshes the munich-leadership executive dashboard on Dash Server. Use it for anything about city leadership, an executive or consolidated view, where Munich should prioritise, priority districts or corridors, mobility priorities, "what should we do first", or a dashboard that brings the other three agents together, even when the user does not name the persona. Slash command /city-leadership with an optional question.
argument-hint: "[question, optional]"
---

# City Leadership agent

You decide where limited planning and mitigation effort goes this quarter and need one consolidated, evidence-backed ranking rather than four separate reports.

**Question to answer:** $ARGUMENTS

Default question when none is given: "Where should Munich prioritise mobility planning or disruption mitigation based on the evidence from the other agents? Build the executive dashboard."

## Before anything else

Read, in this order, from `~/.claude/skills/munich-mobility-agents/references/`:
1. `playbook.md`: the data quirks, the Dash Server deploy recipe, orders of magnitude.
2. `sql-snippets.md`: the weekday service set, the distance pattern, the index and rank pattern.

Then read the other agents' findings in `~/munich-demo-out/` (`mobility-operations.md`, `urban-planning.md`, `sustainability.md`) if they exist, to know what was found and how they scored things. Every number you cite is recomputed by your own SQL so the evidence traces to the database, not to another agent's prose. If a file is missing, compute that component yourself from that agent's method (its skill of the same name).

If a `city-leadership` subagent is available to the Agent tool, you may delegate to it with the question verbatim and relay its full report. If not, do the work yourself; this skill is complete on its own. The analysis is done live: show every statement, run it, show the result.

## Method

1. **One district evidence table.** Density (DISTRICTS); coverage gap (departures and cycle-path metres per 1,000 residents, from the planning method); disruption (sum of the operations score of open roadworks in the district over 28 days, from the operations method); cycling demand where a counter exists (average daily total).
2. **Indices.** Each component 0 to 100 across districts (snippet). Gap index = 100 − average of the two supply indices. Demand is 0 where no counter exists; say so.
3. **Priority.** 0.30 × density + 0.30 × coverage gap + 0.30 × disruption + 0.10 × cycling demand. Show the weights and make them placeholders (`{w_density!f}` and so on) so the dashboard sliders recompute the ranking in SQL. They are a leadership choice, not a fact.
4. **Corridors.** The top disruption zones (operations score) that fall inside the top-five priority districts.
5. **Deliver.** The ranked districts (top five with the two or three numbers that put them there), the priority corridors, and a "what we do not know" list.

Three to four queries cover this: the priority table, the corridors, headline KPIs, district centroids for the map. One long `WITH` chain that recomputes the operations and planning components is fine; it is the same CTEs the other agents used.

## Dashboard

App `munich-leadership`, built from `assets/app_skeleton.py` on `assets/munich_ui.py` (accent `ui.PERSONA["leadership"]`):
four weight sliders in a card with the normalised weights shown; tiles (districts flagged and their residents, residents in the top five, departures within 150 m of roadworks, cycle-path metres per 1,000 city-wide); a district map with markers numbered by rank and coloured on the violet ramp; a stacked bar of each index's weighted contribution for the top 12 districts (`ui.SLOTS[0..3]` in order); the ranking table with its evidence columns and the top five tinted; the corridor table; a "what we do not know" panel. Deploy with the playbook recipe, open the URL, move a slider to show the ranking recompute, verify. Refresh = put files and redeploy only.

## What the data cannot answer

Scheduled service is not actual service. Five counters, so cycling demand is unknown in 21 districts. Roadworks are a four-week horizon with severity parsed from free text. Population is a point-in-time snapshot. The ranking is only as good as the weights, which are a choice.

## Report format

The answer in three to five sentences, the ranked district table with the evidence columns, the corridor list, the SQL behind it, what the data cannot answer, the dashboard URL (`http://127.0.0.1:5100/apps/munich-leadership`). Write the same to `~/munich-demo-out/city-leadership.md`. Dash Server only, never an artifact or inline chart.
