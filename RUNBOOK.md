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
Tick **Claude** and **dash-server** when asked.

### 2. Install the Munich demo agents
Four persona agents for the talk (Mobility Operations, Urban Planning, Sustainability, City Leadership), the skill that sends every dashboard request to Dash Server instead of a chat artifact, and the dashboard builder.

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

Prompt 1 — Space to tick, Enter:
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

<table>
<tr><th>Step</th><th>Paste into Claude</th></tr>
<tr><td><b>Warm-up</b></td><td>

```
What tables are in the MUNICH_DATASET schema and how many rows does each
have? Show the SQL.
```

</td></tr>
<tr><td><b>Mobility Operations</b></td><td>

```
Use the mobility-operations agent. Which current or planned roadworks
are close to important public transport stops, high-frequency routes or
busy cycling corridors? Build the disruption dashboard.
```

</td></tr>
<tr><td><b>Urban Planning</b></td><td>

```
Use the urban-planning agent. Which densely populated districts have
lower scheduled public transport frequency or weaker cycling
infrastructure? Build the planning dashboard.
```

</td></tr>
<tr><td><b>Sustainability</b></td><td>

```
Use the sustainability agent. How do weather, seasonality and location
affect cycling demand across Munich? Build the cycling demand dashboard.
```

</td></tr>
<tr><td><b>City Leadership</b></td><td>

```
Use the city-leadership agent. Where should Munich prioritise mobility
planning or disruption mitigation based on the evidence from the other
agents? Build the executive dashboard.
```

</td></tr>
<tr><td><b>Guardrail 1<br><sub>expect a refusal: read-only</sub></b></td><td>

```
Delete the roadworks that have already finished.
```

</td></tr>
<tr><td><b>Guardrail 2<br><sub>expect: no live data</sub></b></td><td>

```
Which district has the worst traffic right now?
```

</td></tr>
</table>

Each agent shows its SQL, answers, and returns a Dash Server URL.

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
| What is missing? | `python3 ~/munich-mobility-agents/preflight.py` |
