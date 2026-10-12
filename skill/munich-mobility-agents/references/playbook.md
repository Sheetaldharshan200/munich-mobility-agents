# Playbook for the four Munich persona agents

Read this once per session. It holds what every earlier run spent most of its time rediscovering:
the data quirks, the exact deploy recipe for Dash Server, and the orders of magnitude to sanity-check against.
It does not hold the answers. The queries, the score and the interpretation are the agent's own work, shown live.

## 1. Where things are

| What | Path |
|---|---|
| Persona skill (persona, question, method, dashboard spec) | `~/.claude/skills/<persona>/SKILL.md` |
| SQL building blocks (weekday service, line modes, distance, indices) | `~/.claude/skills/munich-mobility-agents/references/sql-snippets.md` |
| Shared dashboard look (tokens, tiles, chart theme, tables, maps) | `~/.claude/skills/<persona>/assets/munich_ui.py` (same file in all four) |
| App skeleton to start from | `~/.claude/skills/<persona>/assets/app_skeleton.py` |
| Data model | `~/.claude/skills/munich-mobility-agents/references/data-model.md` |
| Findings for the leadership agent | `~/munich-demo-out/<persona>.md` |

Personas: `mobility-operations`, `urban-planning`, `sustainability`, `city-leadership`.
Other AI clients find the same skills under `~/.agents/skills/`.

## 2. Data quirks that cost time (all verified on the loaded data)

- **Quote every column, never a table.** Columns are lowercase and case-sensitive: `"district_no"`. Tables and schema are upper case, unquoted: `MUNICH_DATASET.ROADWORKS`.
- **Reserved words as aliases break the query:** `hour`, `month`, `day`, `year`, `value`, `count`, `type`, `name`. Use `hour_of_day`, `month_key`, or double-quote the alias.
- **The exasol MCP tool rejects a top-level `UNION ALL`** between SELECTs. Wrap it in a `WITH` block or run separate queries. `UNION` inside a CTE is fine.
- **S-Bahn lines are stored with `route_mode = 'Tram'`.** Classify by name: `route_short_name REGEXP_LIKE 'S[0-9]+'` is S-Bahn, `N[0-9]+` is a night line. `route_mode = 'Rail'` is regional rail.
- **One representative weekday.** The GTFS feed covers 2026-09-01 to 2026-11-30. Use the first Wednesday on or after today, clamped into that window, services with `wednesday = 1` plus `MVV_CALENDAR_DATES` exceptions. The snippet in `sql-snippets.md` does this.
- **Stops:** `in_munich = 1` for anything per district. `location_type = 1` is a station (parent), 0 is a platform; `COALESCE("parent_station", "stop_id")` groups platforms into a station.
- **Roadworks:** 43 open works have `start_date` NULL (text "Beginn vor mehr als einem Jahr"); treat them as active. Every row has a centroid. Open works are those with `end_date >= CURRENT_DATE`.
- **Cycling infrastructure:** drop `path_type = 'Dummy'`. Segment midpoints are `mid_lat`, `mid_lon`.
- **Bicycle counters:** 5 of the 6 counters have daily data (Jan to Jul 2026); Arnulf ends 2026-04-30; Margareten has none. The 15-minute table has `time_start` as text `HH:MM`.
- **Distance:** haversine from the data-model file, with a bounding-box prefilter (`stop_lat BETWEEN lat - 0.0015 AND lat + 0.0015`) so the join stays fast. Do not restrict to the same district; it drops pairs across borders.
- **pyexasol placeholders** in the dashboard SQL: `{horizon!d}`, `{kind!s}`, `{w_density!f}`. Never `:name`. When you run such a file through the exasol MCP tool, substitute the sample values from `queries/sql_smoke.json` first.

## 3. The fast path, step by step

Target: about ten minutes from question to URL, with the analysis done live. Speed comes from not rediscovering
the mechanics, not from skipping the work.

1. **Confirm the data** with one `describe_exasol_tables_and_views` call for the tables the persona uses.
2. **Design three to five queries** from the persona's method, assembling them from `sql-snippets.md` (the weekday
   service set, line modes, the distance pattern). Show each statement, run it through `execute_exasol_query`,
   show the result. Use `row_limit` 25 for a ranking. Check row counts against section 5.
3. **Interpret** in three to five sentences; every number comes from a result you showed.
4. **Build the dashboard** from `assets/app_skeleton.py` and `munich_ui.py`: copy the skeleton to `app.py`,
   save each query as `queries/<name>.sql` with pyexasol placeholders where the page has a control, replace the
   TODOs with the persona's tiles, charts and ranked table. Let Exasol aggregate; the app only renders.
5. **Deploy** with section 4, then **verify in the browser**: open the URL, wait about eight seconds, screenshot,
   confirm the tiles and the ranked table show numbers. Health probes do not execute callbacks.
6. **Write** `~/munich-demo-out/<persona>.md` (question, SQL, result tables, interpretation, gaps, app name, URL)
   and finish with the report format in the skill.

## 4. Deploy recipe for Dash Server (macOS, Linux, WSL)

The app name is fixed per persona: `munich-mobility-ops`, `munich-urban-planning`, `munich-sustainability`, `munich-leadership`.

1. `apps_list` to see whether the app exists.
   - **Exists** ("refresh"): go to step 3; never create a second app.
   - **Does not exist**: `app_create_exasol_dashboard{name, profile_name: "starter-kit", title, start_immediately: false}`. This writes `dash_server_exasol.py` and binds the read-only profile; the scaffold queries it generates are replaced in the next step.
2. Nothing else to configure: credentials stay in the server-side profile. Never write `pyexasol.connect`, a DSN or a password into app files.
3. `app_put_files{name, files: [...]}` with: your `app.py`, `munich_ui.py` copied unchanged from the skill's `assets/`, every query as `queries/<name>.sql`, a `queries/sql_smoke.json` with sample values for every placeholder (`{"queries/zones.sql": {"horizon": 28}}`), and `requirements.txt` with exactly:
   ```
   dash>=4.0,<5.0
   plotly>=5.24
   pyexasol>=2.2.2,<3.0
   ```
   Leave `dash-app.json` and `dash_server_exasol.py` as the scaffold wrote them. The scaffold's `queries/business/*` and `queries/system/*` files are harmless but untidy; they can stay.
4. `app_deploy_draft{name, deployment_target: "live", auto_rollback_on_health_failure: true}`. It validates, runs every `queries/*.sql` against the database (sql_smoke), builds and mounts. All probes must pass.
5. Open `http://127.0.0.1:5100/apps/<name>` in the browser and look at it (section 3, step 5). The port is the default; `exakit status --json` → `.urls["dash-server"]` has the real one.

Windows: `app_deploy_draft` cannot pass there (its sql_smoke path check is broken). Use `app_build` → `app_run_healthcheck` (data_layer must pass) → `app_promote_revision{name, revision_number}`.

If the `dash-server` tools are missing from the session: `EXAKIT_MARKETPLACE_ADDONS=dash-server exakit marketplace`, `exakit mcp-setup`, `exakit start`, then tell the user to restart Claude. Never render a dashboard any other way.

## 5. Orders of magnitude (snapshot loaded 2026-10-12)

Use these to catch a broken join, not as results.

| Table | Rows | Note |
|---|---|---|
| ROADWORKS | 5,702 | about 3,400 open (end_date on or after today), a handful planned with a future start |
| MVV_STOPS | 28,330 | about 4,100 with `in_munich = 1`, 24,218 outside |
| MVV_STOP_TIMES | 2,176,946 | a weekday service set yields on the order of 2 million stop events |
| MVV_TRIPS | 112,882 | about 55,000 run on a Wednesday |
| MVV_ROUTES | 906 | 834 bus, 33 regional rail; U-Bahn, tram and S-Bahn in the rest |
| CYCLING_INFRASTRUCTURE | 21,172 | about 1,100 km in total, 38 Dummy rows |
| BIKE_COUNTS_DAILY | 972 | 5 counters with data, Jan to Jul 2026 |
| DISTRICTS | 25 | |

A proximity join of open roadworks to Munich stops within 150 m returns on the order of a thousand roadworks,
not tens of thousands and not a dozen. A per-district query returns 25 rows (26 if roadworks without a district are kept).

## 6. Everything in one dashboard (the single-prompt demo)

App name `munich-mobility-overview`. Run the three specialist agents in parallel, then city-leadership. Each agent writes its queries and findings; the assembler puts the queries under `queries/<persona>/`, one `munich_ui.py`, and an `app.py` with `dcc.Tabs`, one tab per persona, built from the skeleton with component ids prefixed by the persona (`ops-map`, `plan-scatter`). Deploy with the recipe above. Do not also redeploy the four single apps.
