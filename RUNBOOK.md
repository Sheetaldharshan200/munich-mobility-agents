# Runbook

### 1. Install Exasol Personal
<https://www.exasol.com/personal/> — copy the command for your OS, run it in a terminal.

macOS / Linux / WSL
```bash
curl https://www.exasol.com/install/starter-kit.sh | sh
```
Windows PowerShell
```powershell
irm https://www.exasol.com/install/starter-kit.ps1 | iex
```
Two installer questions matter for this demo. Use Space to select, Enter to confirm.

- **MCP server, AI clients:** when asked which AI clients to connect to the Exasol MCP server, select **Claude**. It covers both the Claude desktop app and Claude Code.
- **Marketplace, optional add-ons:** when the marketplace selection opens, select **dash-server**. It hosts the dashboards.

Missed either one? Install dash-server first, then connect Claude, so both MCP servers are registered:
```bash
EXAKIT_MARKETPLACE_ADDONS=dash-server exakit marketplace
```
```bash
EXAKIT_MCP_CLIENTS=claude exakit mcp-setup
```

### 2. Install the Munich demo agents
Four persona agents for the talk (Mobility Operations, Urban Planning, Sustainability, City Leadership), the skill that sends every dashboard request to Dash Server instead of a chat artifact (and installs dash-server from the marketplace if it is missing), and the dashboard builder. Applies to Claude Code and to Codex, Cursor, Gemini CLI, OpenCode and Continue when they are on the machine.

macOS / Linux / WSL
```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/sheetaldharshan200/munich-mobility-agents/main/get.sh)"
```
Windows PowerShell
```powershell
irm https://raw.githubusercontent.com/sheetaldharshan200/munich-mobility-agents/main/get.ps1 | iex
```

### 3. Get the data
Download [munich-dataset.zip](https://github.com/sheetaldharshan200/munich-mobility-agents/releases/download/data-v1/munich-dataset.zip) (18 MB) and unzip it. Note the full path of the `munich-dataset` folder, for example `/Users/<your-name>/Downloads/munich-dataset`.

### 4. Load the data
```bash
exakit data-load
```
Answer the three prompts.

Prompt 1 — Space to select, Enter:
```
? What would you like to load?
  [✓] A local CSV / Parquet / JSON file, or a folder of them
```
Prompt 2 — paste the **full** path of the unzipped folder, Enter (`~` does not work here; drag the folder into the terminal to get the full path):
```
? Local CSV / Parquet / JSON file — or a folder of them (type back to return)
```
macOS / Linux example
```
/Users/<your-name>/Downloads/munich-dataset
```
Windows example
```
C:\Users\<your-name>\Downloads\munich-dataset
```
Prompt 3 — paste the schema name, Enter:
```
? Target schema (back to return) [STARTER_KIT]
```
```
MUNICH_DATASET
```
One table per file, 15 tables. The GTFS stop_times file takes the longest.

### 5. Check
```bash
exakit status
```
Database running, dash-server running. Dashboards at <http://127.0.0.1:5100>.

### 6. Demo
**If Claude was already open, quit it and start it again** so it picks up the `exasol` and `dash-server` MCP servers and the new agents.

Claude Code in the terminal:
```bash
claude
```
or the Claude Desktop app → **Code** tab → new session.

There are three ways to run the demo: **A** one dashboard per agent, **B** everything in one dashboard, **C** (optional) the same with the Ask the data box switched on by an API key.

#### A. One prompt per agent, one dashboard each
**Warm-up**
```
What tables are in the MUNICH_DATASET schema and how many rows does each have? Show the SQL.
```
**Mobility Operations**
```
Which current or planned roadworks are close to important public transport stops, high-frequency routes or busy cycling corridors? Build the disruption dashboard.
```
**Urban Planning**
```
Which densely populated districts have lower scheduled public transport frequency or weaker cycling infrastructure? Build the planning dashboard.
```
**Sustainability**
```
How do weather, seasonality and location affect cycling demand across Munich? Build the cycling demand dashboard.
```
**City Leadership**
```
Where should Munich prioritise mobility planning or disruption mitigation based on the evidence from the other agents? Build the executive dashboard.
```
**Guardrail 1 (expect a refusal: read-only)**
```
Delete the roadworks that have already finished.
```
**Guardrail 2 (expect: no live data)**
```
Which district has the worst traffic right now?
```

Each agent shows its SQL, answers, and returns a Dash Server URL. Each agent also has its own skill, which is a slash command: /mobility-operations, /urban-planning, /sustainability, /city-leadership (with or without a question after them).

#### B. One prompt, one combined dashboard
```
Answer all four Munich mobility questions and publish the results as ONE Dash Server dashboard named munich-mobility-overview with four tabs.
Tab 1 Mobility Operations: which current or planned roadworks are close to important public transport stops, high-frequency routes or busy cycling corridors?
Tab 2 Urban Planning: which densely populated districts have lower scheduled public transport frequency or weaker cycling infrastructure?
Tab 3 Sustainability: how do weather, seasonality and location affect cycling demand across Munich?
Tab 4 City Leadership: where should Munich prioritise mobility planning or disruption mitigation, based on the evidence in tabs 1 to 3?
Run the mobility-operations, urban-planning and sustainability agents in parallel, then the city-leadership agent. Give every tab its KPI tiles, ranked table and charts, add the Ask the data box, show the SQL for each tab, say what the data cannot answer, and return one URL.
```
This takes longer than a single agent, because four analyses run before one app is built. The result is one URL, <http://127.0.0.1:5100/apps/munich-mobility-overview>, with a tab per persona.

#### C. Optional: with an Anthropic API key (Ask the data)
Every dashboard has an **Ask the data** box. Set `ANTHROPIC_API_KEY` in a terminal to use this, then restart dash-server from that **same** terminal.

macOS / Linux / WSL
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key
```
```bash
exakit stop && exakit start
```
Windows PowerShell
```powershell
$env:ANTHROPIC_API_KEY = 'sk-ant-your-key'
```
```powershell
exakit stop; exakit start
```
The variable lives only in that terminal session, so repeat the two commands after a reboot. Never paste the key into a chat; a key that lands in a transcript has to be rotated.

Then run prompt **A** or **B**, open the dashboard and type questions into the **Ask the data** box, for example:
```
Which districts have the most roadworks?
```
```
Average daily cyclists per counter on rainy days
```
```
Number of stops per district
```
Each answer shows the SQL it ran.

### 7. Rehearse
Run step 6 the day before; dashboards persist. On stage add this to each prompt:
```
the dashboard already exists, refresh it rather than rebuilding
```

---
| Problem | Run |
|---|---|
| No `dash-server` tools in Claude | `exakit mcp-setup`, restart Claude Code |
| Dashboard page blank / 500 | `exakit stop && exakit start` |
| Ask the data box not working | Set `ANTHROPIC_API_KEY`, then `exakit stop && exakit start` in the same terminal (step 6C) |
| What is missing? | `python3 ~/munich-mobility-agents/preflight.py` |
