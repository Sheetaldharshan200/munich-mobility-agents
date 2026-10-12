# Dashboard routing: Dash Server, never an artifact

## Why this file exists
Without it, an agent asked to "create a dashboard" takes the fastest path it knows: an HTML artifact, a React page, an inline chart or a Markdown table. On this demo every visual result must live on **Dash Server** so the audience sees a hosted, re-openable dashboard built from inspectable SQL on the local Exasol database.

## The rule
Any request whose output is visual — dashboard, chart, graph, plot, view, visualisation, KPI tiles, executive view, report page, "show me" — is built as a Dash Server app. Three layers enforce it on an installed machine:

1. `~/.claude/CLAUDE.md` carries the rule block (between `munich-mobility-agents:start/end` markers).
2. This skill's description triggers on the same words.
3. A `PreToolUse` hook in `~/.claude/settings.json` runs `assets/block_artifacts.py`, which denies the `Artifact` tool (publishing a page) and any `show_widget` tool with a message that points back here. `MUNICH_ALLOW_ARTIFACTS=1` in the environment disables the hook for one session.

## The build path (summary of persona-metrics DEPLOY.md)
1. `python3 ~/.claude/skills/persona-metrics/assets/profile_schema.py MUNICH --json card.json` — the schema card. It is the only description of the data you may rely on.
2. Elicit 2–5 decisions for the persona, derive metrics with `derive_metrics.py`, check coverage, validate signal (`signal_check.py`). Cut flat metrics and say so.
3. `app_create_exasol_dashboard{name: "<app>", profile_name: "starter-kit"}` — scaffold FIRST; it writes `dash_server_exasol.py`, which the builder does not emit.
4. Build the workspace with `build_dashboard.py`, then `app_put_files{name, files}` with every file except `dash_server_exasol.py` and `dash-app.json`.
5. macOS/Linux/WSL: `app_deploy_draft{name, deployment_target: "live", auto_rollback_on_health_failure: true}` then `app_run_healthcheck{name}`.
   Windows: skip `app_deploy_draft` (its `sql_smoke` check cannot pass on Windows): `app_build` → `app_run_healthcheck` (data_layer must be green) → `app_promote_revision{name, revision_number}`.
6. Give the user the URL: `exakit status --json` → `.urls["dash-server"]`, app at `<url>/apps/<app>` (confirm the exact path from `apps_list`).

Design rules that matter on stage (from the dash-server skill): let Exasol compute, Dash renders; never query at import time; `{x}` / `{x!d}` placeholders, never `:name`; check `has_error(rows)` before iterating; read-only profile only.

## App names used by the demo
`munich-mobility-ops`, `munich-urban-planning`, `munich-sustainability`, `munich-leadership`. Reuse them; "refresh" means update the existing app.

## What to say if dash-server is down
"The dash-server add-on is not running, so I cannot build the dashboard yet. Starting it with `exakit start`." Then do that. If the MCP tools are absent from the session: `exakit mcp-setup`, then the user must restart Claude Code. Never substitute another renderer.
