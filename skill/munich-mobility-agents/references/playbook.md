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
- **S-Bahn lines are stored with `route_mode = 'Tram'`.** Classify by name: `REGEXP_INSTR("route_short_name", '^S[0-9]+$') > 0` is S-Bahn, `'^N[0-9]+'` a night line. (The infix `REGEXP_LIKE` form is rejected by the exasol MCP validator; `REGEXP_INSTR` works everywhere.) `route_mode = 'Rail'` is regional rail.
- **One representative weekday.** The GTFS feed covers 2026-09-01 to 2026-11-30. Use the first Wednesday on or after today, clamped into that window, services with `wednesday = 1` plus `MVV_CALENDAR_DATES` exceptions. The snippet in `sql-snippets.md` does this.
- **Stops:** `in_munich = 1` for anything per district. `location_type = 1` is a station (parent), 0 is a platform; `COALESCE("parent_station", "stop_id")` groups platforms into a station.
- **Roadworks:** 43 open works have `start_date` NULL (text "Beginn vor mehr als einem Jahr"); treat them as active. Every row has a centroid. Open works are those with `end_date >= CURRENT_DATE`.
- **Cycling infrastructure:** drop `path_type = 'Dummy'`. Segment midpoints are `mid_lat`, `mid_lon`.
- **Bicycle counters:** 5 of the 6 counters have daily data (Jan to Jul 2026); Arnulf ends 2026-04-30; Margareten has none. The 15-minute table has `time_start` as text `HH:MM`.
- **Distance:** haversine from the data-model file, with a bounding-box prefilter (`stop_lat BETWEEN lat - 0.0015 AND lat + 0.0015`) so the join stays fast. Do not restrict to the same district; it drops pairs across borders.
- **Connection limit:** Exasol Personal allows 20 parallel sessions, and Dash Server keeps some idle after every deploy, so several agents deploying in one session can fill it. If a query, deploy or page load fails with "license limit of 20 parallel connections", wait a few seconds and retry once; do not redesign anything. `app_deploy_draft` with auto-rollback simply needs a second call.
- **pyexasol placeholders** in the dashboard SQL: `{horizon!d}`, `{kind!s}`, `{w_density!f}`. Never `:name`. When you run such a file through the exasol MCP tool, substitute the sample values from `queries/sql_smoke.json` first.

## 3. The fast path: one pass, about 15 tool calls, about five minutes

Almost all of a run's time is the model writing text; the database answers in about a second. So the rule is
simple: write every piece once, keep it short, and do not re-send what you already sent.

| Step | Tool calls |
|---|---|
| 1. `describe_exasol_tables_and_views` for the persona's tables, in one call | 1 |
| 2. Explore only if something is unclear: at most two small queries (a count, a sample), never the full chain | 0 to 2 |
| 3. Run the final queries, each shown before its result, each exactly as the dashboard will use it (placeholders replaced by their sample values). Three or four queries, not ten: one headline row, one ranked table, one or two breakdowns | 3 to 4 |
| 4. Interpret in three to five sentences; every number from a result you showed | 0 |
| 5. `apps_list`, then `app_create_exasol_dashboard` only if the app is missing | 1 to 2 |
| 6. `Read` the skill's `assets/munich_ui.py`, then one `app_put_files` with `app.py` (from `assets/app_skeleton.py`, about 80 lines), `munich_ui.py` unchanged, every query, `queries/sql_smoke.json`, `requirements.txt` | 2 |
| 7. `app_deploy_draft`. If it fails, read the error, fix only the broken file with one more `app_put_files`, deploy again | 1 to 3 |
| 8. One `browser_batch`: navigate, wait 6 s, `get_page_text`, screenshot. Tiles and table must show numbers | 1 |
| 9. One `Write` of `~/munich-demo-out/<persona>.md`, then the report | 1 |

What made earlier runs slow (measured: 80 to 95 % of the time was the model writing text):
- **Re-sending the long shared CTE chain** in ten or more exploratory queries (50,000 characters in one run). Explore small; run the chain only in the three or four final queries.
- **Writing the app twice**: a local file with syntax checks in Bash, then the same content again into `app_put_files`. Write it once, straight into `app_put_files`; `app_deploy_draft` validates it and reports any error.
- **`app_patch_file`** is slow (over a minute per call). Re-put the one file instead.
- **Several browser rounds** with long waits. One batch is enough; the deploy health check already proved the routes.
- **Repeating the SQL** in the findings file and the report. Name the query files and the workspace path instead.
- **Long reports.** The answer, the top 10 rows (the full table is on the dashboard), the gaps, the URL.

## 4. Deploy recipe for Dash Server (macOS, Linux, WSL)

The app name is fixed per persona: `munich-mobility-ops`, `munich-urban-planning`, `munich-sustainability`, `munich-leadership`.

1. `apps_list` to see whether the app exists.
   - **Exists** ("refresh"): go to step 3; never create a second app.
   - **Does not exist**: `app_create_exasol_dashboard{name, profile_name: "starter-kit", title, start_immediately: false}`. This writes `dash_server_exasol.py` and binds the read-only profile; the scaffold queries it generates are replaced in the next step.
2. Nothing else to configure: credentials stay in the server-side profile. Never write `pyexasol.connect`, a DSN or a password into app files.
3. One `app_put_files{name, files: [...]}` with: your `app.py` (from `assets/app_skeleton.py`), `munich_ui.py` unchanged from the skill's `assets/`, every query as `queries/<name>.sql`, a `queries/sql_smoke.json` with sample values for every placeholder (`{"queries/ranking.sql": {"horizon": 28}}`), and `requirements.txt` with exactly:
   ```
   dash>=4.0,<5.0
   plotly>=5.24
   pyexasol>=2.2.2,<3.0
   ```
   Leave `dash-app.json` and `dash_server_exasol.py` as the scaffold wrote them. The scaffold's `queries/business/*` and `queries/system/*` files are harmless but untidy; they can stay.
4. `app_deploy_draft{name, deployment_target: "live", auto_rollback_on_health_failure: true}`. It validates, runs every `queries/*.sql` against the database (sql_smoke), builds and mounts. All probes must pass.
5. Open `http://127.0.0.1:5100/apps/<name>` in one browser batch and look at it (section 3, step 8). The port is the default; `exakit status --json` → `.urls["dash-server"]` has the real one.

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
