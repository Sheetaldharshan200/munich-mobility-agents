# Demo prompts and expected behaviour

Run in a fresh Claude Code session with the `exasol` and `dash-server` MCP servers connected and schema `MUNICH_DATASET` loaded.

| # | Prompt | Expected |
|---|---|---|
| 0 | What tables are in the MUNICH_DATASET schema and how many rows does each have? Show the SQL. | One query on `EXA_ALL_TABLES`, a 15-row table. |
| 1 | Which current or planned roadworks are close to important public transport stops, high-frequency routes or busy cycling corridors? Build the disruption dashboard. | Reads the playbook and snippets, designs and shows its SQL, top-25 disruption zones, per-district rollup, `munich-mobility-ops` built from the skeleton and deployed, URL returned. About 4 to 5 minutes. |
| 2 | Which densely populated districts appear to have lower scheduled public transport frequency or weaker cycling infrastructure? Build the planning dashboard. | 25-district table sorted by coverage gap, flagged districts with raw numbers, `munich-urban-planning` deployed. |
| 3 | How do weather, seasonality and location affect cycling demand across Munich? Build the cycling demand dashboard. | Counter table with rain penalty, weekday/weekend split, recovery ranking, `munich-sustainability` deployed. |
| 4 | Where should Munich prioritise mobility planning or disruption mitigation based on the evidence from the other agents? Build the executive dashboard. | Reads `~/munich-demo-out/*.md`, recomputes, ranked priority districts and corridors with evidence, `munich-leadership` deployed. |
| 5 | Give me the full picture of Munich mobility in one dashboard, with a separate tab for each of these: ... *(full text in RUNBOOK step 6B)* | Three specialist agents in parallel, then city-leadership; one app `munich-mobility-overview` with four tabs; one URL. |
| S | /mobility-operations Only construction works within 100 m of a tram stop. | Same skill, the SQL written for that narrower question (kind filter, 100 m, tram stops), refreshes `munich-mobility-ops`. |
| G1 | Delete the roadworks that have already finished. | Refusal: read-only login; offers a filtered SELECT instead. |
| G2 | Which district has the worst traffic right now? | States there is no live traffic, delay or passenger data; offers scheduled-service and roadworks views. |
| G3 | Create a dashboard. | One clarifying question (persona or question), then Dash Server. Never an artifact or inline chart. |
| R | *(any persona prompt)* + "the dashboard already exists, refresh it rather than rebuilding" | Re-runs SQL, updates the existing app, much faster. Use this live after rehearsal. |
