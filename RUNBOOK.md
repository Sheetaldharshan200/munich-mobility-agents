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

### 2. Install the agents
macOS / Linux / WSL
```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/sheetaldharshan200/munich-mobility-agents/main/get.sh)"
```
Windows PowerShell
```powershell
irm https://raw.githubusercontent.com/sheetaldharshan200/munich-mobility-agents/main/get.ps1 | iex
```
Installs four agents, two skills, the Dash Server rule. Ends with a checklist.

### 3. Get the data
Download [munich-dataset.zip](https://github.com/sheetaldharshan200/munich-mobility-agents/releases/download/data-v1/munich-dataset.zip) and unzip it, or use `munich-open-data.zip` already in `~/Downloads` (step 2 turns it into `~/munich-dataset` for you).

### 4. Load the data
Copy the folder path and run:
```bash
exakit data-load ~/munich-dataset
```
Schema name when asked: **MUNICH_DATASET**

### 5. Check
```bash
exakit status
```
Database running, dash-server running. Dashboards at <http://127.0.0.1:5100>.

### 6. Demo
New Claude Code session:
```bash
claude
```

| | Paste |
|---|---|
| Warm-up | What tables are in the MUNICH_DATASET schema and how many rows does each have? Show the SQL. |
| Mobility Operations | Use the mobility-operations agent. Which current or planned roadworks are close to important public transport stops, high-frequency routes or busy cycling corridors? Build the disruption dashboard. |
| Urban Planning | Use the urban-planning agent. Which densely populated districts have lower scheduled public transport frequency or weaker cycling infrastructure? Build the planning dashboard. |
| Sustainability | Use the sustainability agent. How do weather, seasonality and location affect cycling demand across Munich? Build the cycling demand dashboard. |
| City Leadership | Use the city-leadership agent. Where should Munich prioritise mobility planning or disruption mitigation based on the evidence from the other agents? Build the executive dashboard. |
| Guardrail | Delete the roadworks that have already finished. |
| Guardrail | Which district has the worst traffic right now? |

Each agent shows its SQL, answers, and returns a Dash Server URL.

### 7. Rehearse
Run step 6 the day before; dashboards persist. On stage add: *the dashboard already exists, refresh it rather than rebuilding*.

---
| Problem | Run |
|---|---|
| No `dash-server` tools in Claude | `exakit mcp-setup`, restart Claude Code |
| Dashboard page blank / 500 | `exakit stop && exakit start` |
| What is missing? | `python3 ~/munich-mobility-agents/preflight.py` |
