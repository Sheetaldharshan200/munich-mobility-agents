# Munich in Motion — Four Data Agents, One Data Foundation

Public Munich mobility data in Exasol Personal on a laptop. Four persona agents in Claude Code ask real planning questions, show the SQL, and publish persona dashboards on Dash Server. Reproducible by anyone in the room.

**Pitch:** agentic data intelligence is not four chatbots on four datasets. It is four specialised agents, one governed read-only data foundation, transparent SQL, and dashboards you can open.

**Start here: [RUNBOOK.md](RUNBOOK.md)** — seven steps, copy and run.

| | |
|---|---|
| [RUNBOOK.md](RUNBOOK.md) | Steps, commands, prompts |
| [AGENTS.md](AGENTS.md) | The four agents: question, data, method, dashboard, guardrails |
| [agents/](agents/) | Claude Code subagent files |
| [skill/mobility-operations/](skill/mobility-operations/SKILL.md) · [skill/urban-planning/](skill/urban-planning/SKILL.md) · [skill/sustainability/](skill/sustainability/SKILL.md) · [skill/city-leadership/](skill/city-leadership/SKILL.md) | One skill per agent: question, method, dashboard, rules. Also the slash commands `/mobility-operations` etc.; works even when the subagent is not loaded |
| [skill/munich-mobility-agents/](skill/munich-mobility-agents/SKILL.md) | Routing skill: dashboard → Dash Server, persona → agent, data model |
| [skill/persona-metrics/](skill/persona-metrics/SKILL.md) | Dashboard pipeline (vendored from [yuvi-ex/dashserverskills](https://github.com/yuvi-ex/dashserverskills), Ask-the-data panel kept; Anthropic key optional via `ANTHROPIC_API_KEY`) |
| [scripts/prepare_dataset.py](scripts/prepare_dataset.py) | Portal download → flat, clean, district-tagged CSVs |
| [Release: munich-dataset.zip](https://github.com/sheetaldharshan200/munich-mobility-agents/releases/download/data-v1/munich-dataset.zip) | The load-ready data (18 MB) |
| [docs/data-verification.md](docs/data-verification.md) | Source vs. loaded row counts, every table |
| [docs/talk-track.md](docs/talk-track.md) | Talk concept and 35-minute flow |

## Data

| Dataset | Source | Tables |
|---|---|---|
| Bicycle counts 2026 (15-min, daily + weather) | [opendata.muenchen.de](https://opendata.muenchen.de/dataset?q=raddauerz%C3%A4hlstellen+2026) | BIKE_COUNTS_DAILY, BIKE_COUNTS_15MIN, BIKE_COUNT_STATIONS |
| MVV schedules (GTFS) | [MVV developer area](https://www.mvv-muenchen.de/fahrplanauskunft/fuer-entwickler/opendata/index.html) | MVV_STOPS, MVV_ROUTES, MVV_TRIPS, MVV_STOP_TIMES, MVV_CALENDAR, MVV_CALENDAR_DATES, MVV_AGENCY |
| Current and planned roadworks | [opendata.muenchen.de](https://opendata.muenchen.de/dataset?q=baustellen) | ROADWORKS |
| Population and boundaries, 25 districts | [opendata.muenchen.de](https://opendata.muenchen.de/dataset?q=stadtbezirke) | DISTRICTS |
| Cycling infrastructure | [opendata.muenchen.de](https://opendata.muenchen.de/dataset?q=radwege) | CYCLING_INFRASTRUCTURE |

Schema `MUNICH_DATASET`. Scheduled service only: no passengers, delays or live traffic. Nothing synthetic.

Links: [Exasol Personal](https://www.exasol.com/personal/) · [Starter Kit](https://github.com/exasol-labs/exasol-personal-local-starterkit) · [dash-server](https://github.com/exasol-labs/dash-server) · [Exasol MCP server](https://github.com/exasol/mcp-server)
