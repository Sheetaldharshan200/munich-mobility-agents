# Munich in Motion — Four Data Agents, One Data Foundation

Public Munich mobility data in Exasol Personal on a laptop. Four persona agents in Claude Code ask real planning questions, show the SQL, and publish persona dashboards on Dash Server. Reproducible by anyone in the room.

**Pitch:** agentic data intelligence is not four chatbots on four datasets. It is four specialised agents, one governed read-only data foundation, transparent SQL, and dashboards you can open.

---

## Setup

**1. Exasol Personal** — from <https://www.exasol.com/personal/>

```bash
curl https://www.exasol.com/install/starter-kit.sh | sh
```
Windows PowerShell:
```powershell
irm https://www.exasol.com/install/starter-kit.ps1 | iex
```
Tick **Claude** and **dash-server** when asked. Otherwise: `exakit marketplace dash-server` and `exakit mcp-setup`.

**2. Agents + skill** (this package, plus persona-metrics)

```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/sheetaldharshan200/munich-mobility-agents/main/get.sh)"
```
Windows PowerShell:
```powershell
irm https://raw.githubusercontent.com/sheetaldharshan200/munich-mobility-agents/main/get.ps1 | iex
```

**3. Data** — `munich-open-data.zip`, flattened and loaded into schema `MUNICH`

```bash
python3 ~/.claude/skills/munich-mobility-agents/assets/prepare_dataset.py ~/Downloads/munich-open-data.zip --out ~/munich-open-data
```
```bash
EXAKIT_SCHEMA=MUNICH exakit data-load ~/munich-open-data
```

**4. Check**

```bash
exakit status
```
Dashboards: <http://127.0.0.1:5100>

---

## Demo — in a fresh `claude` session

| | Prompt |
|---|---|
| Warm-up | What tables are in the MUNICH schema and how many rows does each have? Show the SQL. |
| Mobility Operations | Use the mobility-operations agent. Which current or planned roadworks are close to important public transport stops, high-frequency routes or busy cycling corridors? Build the disruption dashboard. |
| Urban Planning | Use the urban-planning agent. Which densely populated districts have lower scheduled public transport frequency or weaker cycling infrastructure? Build the planning dashboard. |
| Sustainability | Use the sustainability agent. How do weather, seasonality and location affect cycling demand across Munich? Build the cycling demand dashboard. |
| City Leadership | Use the city-leadership agent. Where should Munich prioritise mobility planning or disruption mitigation based on the evidence from the other agents? Build the executive dashboard. |
| Guardrail | Delete the roadworks that have already finished. |
| Guardrail | Which district has the worst traffic right now? |

Every dashboard request lands on Dash Server, never a chat artifact. Rehearsed dashboards persist; live, add *"the dashboard already exists, refresh it"* to the prompt.

---

## Data

| Dataset | Source | Tables |
|---|---|---|
| Bicycle counts 2026 (15-min, daily + weather) | [opendata.muenchen.de](https://opendata.muenchen.de/dataset?q=raddauerz%C3%A4hlstellen+2026) | BIKE_COUNTS_DAILY, BIKE_COUNTS_15MIN, BIKE_COUNT_STATIONS |
| MVV schedules (GTFS) | [MVV developer area](https://www.mvv-muenchen.de/fahrplanauskunft/fuer-entwickler/opendata/index.html) | MVV_STOPS, MVV_ROUTES, MVV_TRIPS, MVV_STOP_TIMES, MVV_CALENDAR, MVV_CALENDAR_DATES, MVV_AGENCY |
| Current and planned roadworks | [opendata.muenchen.de](https://opendata.muenchen.de/dataset?q=baustellen) | ROADWORKS |
| Population and boundaries, 25 districts | [opendata.muenchen.de](https://opendata.muenchen.de/dataset?q=stadtbezirke) | DISTRICTS |
| Cycling infrastructure | [opendata.muenchen.de](https://opendata.muenchen.de/dataset?q=radwege) | CYCLING_INFRASTRUCTURE |
| MVG bike trips 2015–2025 (optional, historical) | [opendata.muenchen.de](https://opendata.muenchen.de/dataset?q=mvg+rad+fahrten) | MVG_BIKE_TRIPS |

Scheduled service only: no passengers, delays or live traffic. Nothing synthetic.

---

## In this package

| | |
|---|---|
| [AGENTS.md](AGENTS.md) | The four agents: question, data, method, dashboard, guardrails |
| [agents/](agents/) | Claude Code subagent files |
| [skill/munich-mobility-agents/](skill/munich-mobility-agents/SKILL.md) | Routing skill: dashboard → Dash Server; persona → agent; data model |
| [scripts/prepare_dataset.py](scripts/prepare_dataset.py) | Portal download → flat, clean, district-tagged CSVs |
| [docs/talk-track.md](docs/talk-track.md) | Talk concept and 35-minute flow |

Links: [Starter Kit](https://github.com/exasol-labs/exasol-personal-local-starterkit) · [dash-server](https://github.com/exasol-labs/dash-server) · [persona-metrics](https://github.com/yuvi-ex/dashserverskills) · [Exasol MCP server](https://github.com/exasol/mcp-server)
