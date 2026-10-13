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
- **MCP server, AI clients:** when asked which AI clients to connect to the Exasol MCP server, select **Claude**. It covers both the Claude desktop app and Claude Code.
- **Marketplace, optional add-ons:** when the marketplace selection opens, select **dash-server**. It hosts the dashboards.

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
Prompt 2 — paste the **full** path of the unzipped folder, Enter:
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

There are three ways to run the demo: **A** one dashboard per agent, **B** everything in one dashboard, **C** (optional) a free-form persona with the Ask the data box, switched on by an API key.

Each agent follows its skill: it reads the shared playbook and SQL building blocks, designs its own queries for the question and runs them in front of you, interprets the results, builds the dashboard from the shared skeleton and look, deploys it on Dash Server, opens it to verify, and returns the URL. Expect about ten minutes per agent; the same prompt a second time refreshes the existing app and is faster.

#### A. One prompt per agent, one dashboard each
**Warm-up**
```
What tables are in the MUNICH_DATASET schema and how many rows does each have? Show the SQL.
```
**Mobility Operations** → `munich-mobility-ops`
```
Which current or planned roadworks are close to important public transport stops, high-frequency routes or busy cycling corridors? Build the disruption dashboard.
```
**Urban Planning** → `munich-urban-planning`
```
Which densely populated districts have lower scheduled public transport frequency or weaker cycling infrastructure? Build the planning dashboard.
```
**Sustainability** → `munich-sustainability`
```
How do weather, seasonality and location affect cycling demand across Munich? Build the cycling demand dashboard.
```
**City Leadership** → `munich-leadership` (run it last; it reads the other three findings)
```
Where should Munich prioritise mobility planning or disruption mitigation based on the evidence from the other agents? Build the executive dashboard.
```
Each of the four is also a slash command that runs the same default question: `/mobility-operations`, `/urban-planning`, `/sustainability`, `/city-leadership`. Add your own question after the command to change it, for example:
```
/mobility-operations Only construction works within 100 m of a tram stop.
```
```
/city-leadership Weight roadwork disruption at 0.6 and ignore cycling demand.
```
**Guardrail 1 (expect a refusal: read-only)**
```
Delete the roadworks that have already finished.
```
**Guardrail 2 (expect: no live data)**
```
Which district has the worst traffic right now?
```

#### B. One prompt, one combined dashboard
```
Give me the full picture of Munich mobility in one dashboard, with a separate tab for each of these:
- which current or planned roadworks are close to important public transport stops, high-frequency routes or busy cycling corridors
- which densely populated districts have lower scheduled public transport frequency or weaker cycling infrastructure
- how weather, seasonality and location affect cycling demand across the city
- and, based on all of that, where Munich should prioritise mobility planning or disruption mitigation

Each tab needs its own headline numbers, a ranked table and charts. Be clear about what the data can't tell us, and give me one link at the end.
```
This takes longer than a single agent, because four analyses run before one app is built. The result is one URL, <http://127.0.0.1:5100/apps/munich-mobility-overview>, with a tab per persona.

#### C. Optional: a free-form persona with Ask the data (needs an Anthropic API key)
The four persona dashboards above are fixed designs. Any other persona goes through the generic dashboard builder, and those dashboards carry an **Ask the data** box that turns a typed question into SQL, runs it read-only and shows the query. To use it:

**1. Set the key** in a terminal, then restart dash-server from that same terminal.

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
The key lasts only for that terminal session, so repeat this after a reboot. Never paste the key into a chat; a key that lands in a transcript has to be rotated.

**2. Build a dashboard for a persona outside the four**, for example:
```
Build a dashboard for the head of the MVV bus network on the MUNICH_DATASET schema: which bus lines run most often, where their stops cluster, and which of them have roadworks beside a stop this month.
```

**3. Ask questions on Dash Server.** Open the URL Claude returns, then type a question into the **Ask the data** box, for example:
```
Which districts have the most roadworks?
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
