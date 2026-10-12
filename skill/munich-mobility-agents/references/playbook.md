# Playbook for the four Munich persona agents

Read this once per session. It holds what every earlier run spent most of its time rediscovering:
the data quirks, the exact deploy recipe for Dash Server, and the baseline numbers to sanity-check against.

## 1. Where things are

| What | Path |
|---|---|
| Persona skill (method, bundled SQL, dashboard) | `~/.claude/skills/<persona>/SKILL.md` with `queries/*.sql` and `assets/app.py` |
| Shared dashboard look (tokens, tiles, chart theme) | `~/.claude/skills/<persona>/assets/munich_ui.py` (same file in all four) |
| Data model | `~/.claude/skills/munich-mobility-agents/references/data-model.md` |
| Findings for the leadership agent | `~/munich-demo-out/<persona>.md` |

Personas: `mobility-operations`, `urban-planning`, `sustainability`, `city-leadership`.
Other AI clients find the same skills under `~/.agents/skills/`.

## 2. Data quirks that cost time (all verified on the loaded data)

- **Quote every column, never a table.** Columns are lowercase and case-sensitive: `"district_no"`. Tables and schema are upper case, unquoted: `MUNICH_DATASET.ROADWORKS`.
- **Reserved words as aliases break the query:** `hour`, `month`, `day`, `year`, `value`, `count`, `type`, `name`. Use `hour_of_day`, `month_key`, or double-quote the alias.
- **The exasol MCP tool rejects a top-level `UNION ALL`** between SELECTs. Wrap it in a `WITH` block or run separate queries. `UNION` inside a CTE is fine.
- **S-Bahn lines are stored with `route_mode = 'Tram'`.** Classify by name: `route_short_name REGEXP_LIKE 'S[0-9]+'` is S-Bahn, `N[0-9]+` is a night line. `route_mode = 'Rail'` is regional rail.
- **One representative weekday.** The GTFS feed covers 2026-09-01 to 2026-11-30. Use the first Wednesday on or after today, clamped into that window, services with `wednesday = 1` plus `MVV_CALENDAR_DATES` exceptions. The bundled SQL does this.
- **Stops:** `in_munich = 1` for anything per district. `location_type = 1` is a station (parent), 0 is a platform; `COALESCE("parent_station", "stop_id")` groups platforms into a station.
- **Roadworks:** 43 open works have `start_date` NULL (text "Beginn vor mehr als einem Jahr"); treat them as active. Every row has a centroid. Open works are those with `end_date >= CURRENT_DATE`.
- **Cycling infrastructure:** drop `path_type = 'Dummy'`. Segment midpoints are `mid_lat`, `mid_lon`.
- **Bicycle counters:** 5 of the 6 counters have daily data (Jan to Jul 2026); Arnulf ends 2026-04-30; Margareten has none. The 15-minute table has `time_start` as text `HH:MM`.
- **Distance:** haversine from the data-model file, with a bounding-box prefilter (`stop_lat BETWEEN lat - 0.0015 AND lat + 0.0015`) so the join stays fast. Do not restrict to the same district; it drops pairs across borders.
- **pyexasol placeholders** in the dashboard SQL: `{horizon!d}`, `{kind!s}`, `{w_density!f}`. Never `:name`. When you run such a file through the exasol MCP tool, substitute the sample values from `queries/sql_smoke.json` first.

## 3. The fast path, step by step

Target: under ten minutes from question to URL. The bundled SQL is already tested, so the work is to run it, explain it, deploy it.

1. **Confirm the data** with one `describe_exasol_tables_and_views` call for the tables the persona uses. Skip the row counts; they are in section 5.
2. **Run the bundled queries** through `execute_exasol_query`, showing each statement before its result. Use `row_limit` 25 for the ranking query. Substitute placeholders with the `sql_smoke.json` values. Compare the headline numbers with section 5; a mismatch means the data changed, say so.
3. **Interpret** in three to five sentences, every number taken from a result you showed.
4. **Deploy** with the recipe in section 4.
5. **Verify in the browser**, not just with the health check: open the URL, wait about eight seconds, take a screenshot, confirm the tiles and the ranked table show numbers. Health probes do not execute callbacks.
6. **Write** `~/munich-demo-out/<persona>.md` (question, SQL, result tables, interpretation, gaps, app name, URL) and finish with the report format in the skill.

If the question is the persona's default question, do not redesign anything. If it differs, change only the query that needs changing and keep the shared CTEs (`feed`, `rd`, `svc`, `lines`, `wt`, `ev`, `stp`); they are the slow part to get right.

## 4. Deploy recipe for Dash Server (macOS, Linux, WSL)

The app name is fixed per persona: `munich-mobility-ops`, `munich-urban-planning`, `munich-sustainability`, `munich-leadership`.

1. `apps_list` to see whether the app exists.
   - **Exists** ("refresh"): go to step 3; never create a second app.
   - **Does not exist**: `app_create_exasol_dashboard{name, profile_name: "starter-kit", title, start_immediately: false}`. This writes `dash_server_exasol.py` and binds the read-only profile; the scaffold queries it generates are replaced in the next step.
2. Nothing else to configure: credentials stay in the server-side profile. Never write `pyexasol.connect`, a DSN or a password into app files.
3. `app_put_files{name, files: [...]}` with, from the persona skill folder: `assets/app.py` as `app.py`, `assets/munich_ui.py` as `munich_ui.py`, every `queries/*.sql` as `queries/<file>.sql`, `queries/sql_smoke.json` if the skill has one, and `requirements.txt` with exactly:
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

## 5. Baseline numbers (snapshot loaded 2026-10-12; today = 2026-10-12, reference weekday 2026-10-14)

| Persona | Headline results |
|---|---|
| mobility-operations | 3,370 open roadworks, 6 planned; 1,525 within 150 m of a stop; 199,764 weekday departures at those stops; 52 of 62 high-frequency lines touched; top zone Frankfurter Ring 149 (score 17.44) |
| urban-planning | 1,440 residents per station; 249.3 departures per 1,000 residents; 698 cycle-path m per 1,000; 8 districts flagged (437,489 residents); biggest gap Schwabing-West (22.0) |
| sustainability | 2,211,015 cyclists counted, 5 counters; busiest Erhardtstr. (4,765 per day); rain penalty 31 to 37 %, average 34 %; weekday/weekend ratio 1.18 (Erhardt) to 2.07 (Hirsch); Hirsch recovers best (1.03) |
| city-leadership | default weights 0.3/0.3/0.3/0.1: Ludwigsvorstadt-Isarvorstadt first (80.2), then Schwabing-West, Au-Haidhausen, Maxvorstadt, Neuhausen-Nymphenburg; 336,998 residents in the top five |

Table row counts: ROADWORKS 5,702; MVV_STOPS 28,330; MVV_STOP_TIMES 2,176,946; MVV_TRIPS 112,882; CYCLING_INFRASTRUCTURE 21,172; BIKE_COUNTS_DAILY 972; DISTRICTS 25.

## 6. Everything in one dashboard (the single-prompt demo)

App name `munich-mobility-overview`. Run the three specialist agents in parallel, then city-leadership, then build one app: copy each persona's `queries/*.sql` into `queries/<persona>/`, one `munich_ui.py`, and an `app.py` with `dcc.Tabs`, one tab per persona. Each tab's layout and callbacks are the persona's `assets/app.py` with component ids prefixed by the persona (`ops-map`, `plan-scatter`) and query paths pointing at the sub-folder. Deploy with the recipe above. Do not also redeploy the four single apps.
