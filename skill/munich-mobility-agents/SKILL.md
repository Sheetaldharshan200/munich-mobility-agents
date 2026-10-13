---
name: munich-mobility-agents
description: Route every dashboard, chart or persona request on the Munich open-data demo to Dash Server and to the right persona agent. Use whenever a request mentions a dashboard, chart, graph, plot, view, visualisation, KPI page or executive view (even a bare "create a dashboard"), or names a Munich persona — mobility operations, urban planning, sustainability, city leadership — or the MUNICH_DATASET schema (roadworks, MVV stops and routes, bicycle counters, districts, cycling infrastructure). Triggers — "create a dashboard", "build a dashboard", "make a chart", "visualise this", "show me a view", "executive view", "mobility operations", "urban planning", "sustainability agent", "city leadership", "Munich", "MUNICH_DATASET schema", "roadworks", "Baustellen", "MVV", "bike counts".
---

# munich-mobility-agents

Two jobs, in this order:

## 1. Dashboards go to Dash Server. No exceptions.

Read `references/dashboard-routing.md`. The short version:

- "Dashboard", "chart", "graph", "plot", "view", "visualise", "KPI page", "executive view" → build a **Dash Server** app through the `dash-server` MCP control plane using the `persona-metrics` skill (`~/.claude/skills/persona-metrics/SKILL.md`, deploy recipe in its `DEPLOY.md`). Hand back the URL from `exakit status --json` (default `http://127.0.0.1:5100`).
- Never an Artifact, HTML/React page, `show_widget`, inline SVG, matplotlib/plotly image, Streamlit app, or a Markdown table labelled "dashboard". A `PreToolUse` hook (`assets/block_artifacts.py`) blocks the Artifact and widget tools on demo machines; if you hit it, that is the rule working, not an error to route around.
- `dash-server` tools missing from the session → If the dash-server tools are missing, do not stop and do not fall back: install the add-on with `exakit marketplace dash-server`, register it with `exakit mcp-setup`, start it with `exakit start`, confirm with `exakit status`, then tell the user to restart Claude so the dash-server tools load, and continue from there. Never fall back to another renderer.
- Bare "create a dashboard" with no subject → ask one question (which persona or which question), then build on Dash Server.
- "The dashboard already exists, refresh it" → update the existing app (`app_put_files` + redeploy), do not create a second one.

## 2. Persona questions go to the persona agent.

| The request is about | Subagent (`~/.claude/agents/`) | App name |
|---|---|---|
| roadworks near stops, routes, cycling corridors; disruption | `mobility-operations` | `munich-mobility-ops` |
| population vs scheduled transport and cycling coverage per district | `urban-planning` | `munich-urban-planning` |
| cycling demand, weather, seasonality, counters | `sustainability` | `munich-sustainability` |
| consolidated priorities across all of the above; executive view | `city-leadership` | `munich-leadership` |

Each persona has its own skill with the full method and dashboard spec; the agent writes its SQL live from `references/sql-snippets.md` and builds the dashboard from the shared skeleton and look under the skill's `assets/`: `mobility-operations`, `urban-planning`, `sustainability`, `city-leadership` (installed next to this one, also the slash commands of the same name). If the subagent is not available, load that skill and follow it in this session.

**Several persona questions in one request, one dashboard with tabs or sections** (for example "the full picture of Munich mobility in one dashboard, a tab for each of these") → run `mobility-operations`, `urban-planning` and `sustainability` in parallel, then `city-leadership`, and build ONE Dash Server app `munich-mobility-overview` with a tab per persona (each tab carries that agent's KPI tiles, ranked table and charts) plus the Ask-the-data box. Do not also deploy the four single-persona apps.

Delegate with the Agent tool (`subagent_type` = the name above) and pass the user's question verbatim. Relay the subagent's report: answer, ranked table, gaps, dashboard URL. If subagents are unavailable, load that persona's skill (same name) and follow its method yourself.

## Working rules for any query on MUNICH_DATASET

- Start with `references/playbook.md` (data quirks, the Dash Server deploy recipe, orders of magnitude) and `references/sql-snippets.md` (building blocks). Then `references/data-model.md` (tables, columns, joins, date casting, haversine distance, known gaps). Column names are lowercase and must be double-quoted in SQL (`"district_no"`); confirm with `describe_exasol_tables_and_views` before writing SQL.
- Show the SQL, run it through the read-only `exasol` MCP server, show the result, then interpret. Every number in an answer comes from a query that was shown.
- Say what the data cannot answer. MVV GTFS is scheduled service: no passengers, delays, crowding or live traffic. Six bicycle counters are not the whole city. Nothing here is synthetic.
- Write requests (delete, update, create table) are refused: the MCP login is read-only and the database enforces it.
- Demo prompts and expected behaviour: `references/demo-prompts.md`.
