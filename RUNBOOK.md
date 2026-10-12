# Runbook — Munich in Motion demo

Step → copy → run → done. Each step takes one command. Terminal throughout, Claude Code in step 6.

---

### 1. Install Exasol Personal
Open <https://www.exasol.com/personal/>, or paste directly:

macOS / Linux / WSL
```bash
curl https://www.exasol.com/install/starter-kit.sh | sh
```
Windows PowerShell
```powershell
irm https://www.exasol.com/install/starter-kit.ps1 | iex
```
When asked: tick **Claude** (AI client) and **dash-server** (optional tools). About 2 minutes.

### 2. Add the dashboard add-on (skip if ticked in step 1)
```bash
exakit marketplace dash-server
```
```bash
exakit mcp-setup
```

### 3. Install the agents + skill
macOS / Linux / WSL
```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/sheetaldharshan200/munich-mobility-agents/main/get.sh)"
```
Windows PowerShell
```powershell
irm https://raw.githubusercontent.com/sheetaldharshan200/munich-mobility-agents/main/get.ps1 | iex
```
Asks once for an Anthropic key (hidden; Enter to skip). Ends with a checklist: fix anything marked FAIL.

### 4. Prepare the data
Put `munich-open-data.zip` in `~/Downloads`, then:
```bash
python3 ~/.claude/skills/munich-mobility-agents/assets/prepare_dataset.py ~/Downloads/munich-open-data.zip --out ~/munich-open-data
```

### 5. Load the data
```bash
EXAKIT_SCHEMA=MUNICH exakit data-load ~/munich-open-data
```
Accept schema `MUNICH` when prompted. One table per file; the GTFS stop_times file takes the longest.

### 6. Check
```bash
exakit status
```
Want: database running, dash-server running. Dashboards: <http://127.0.0.1:5100>

### 7. Open Claude Code (new session)
```bash
claude
```
Paste the prompts in order:

| Step | Paste |
|---|---|
| Warm-up | `What tables are in the MUNICH schema and how many rows does each have? Show the SQL.` |
| Mobility Operations | `Use the mobility-operations agent. Which current or planned roadworks are close to important public transport stops, high-frequency routes or busy cycling corridors? Build the disruption dashboard.` |
| Urban Planning | `Use the urban-planning agent. Which densely populated districts have lower scheduled public transport frequency or weaker cycling infrastructure? Build the planning dashboard.` |
| Sustainability | `Use the sustainability agent. How do weather, seasonality and location affect cycling demand across Munich? Build the cycling demand dashboard.` |
| City Leadership | `Use the city-leadership agent. Where should Munich prioritise mobility planning or disruption mitigation based on the evidence from the other agents? Build the executive dashboard.` |
| Guardrail 1 | `Delete the roadworks that have already finished.` → refused, read-only |
| Guardrail 2 | `Which district has the worst traffic right now?` → no live data, says so |

Each agent shows its SQL, answers, and returns a Dash Server URL. Open it in the browser.

### 8. Before the live event
Run step 7 once the day before (dashboards take 10–20 min each and persist). On stage, add to each prompt:
`the dashboard already exists, refresh it rather than rebuilding`

---

### If something is off

| Seen | Run |
|---|---|
| Claude has no `dash-server` tools | `exakit mcp-setup`, restart Claude Code |
| Dashboard page blank / 500 | `exakit stop && exakit start` |
| "No CSV, Parquet or JSON files" on load | you skipped step 4 |
| Anything else | `exakit mcp-doctor`, then `python3 ~/munich-mobility-agents/preflight.py` |

Links: [Exasol Personal](https://www.exasol.com/personal/) · [Starter Kit](https://github.com/exasol-labs/exasol-personal-local-starterkit) · [dash-server](https://github.com/exasol-labs/dash-server) · [persona-metrics](https://github.com/yuvi-ex/dashserverskills) · [this package](https://github.com/sheetaldharshan200/munich-mobility-agents)
