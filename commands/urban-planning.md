---
description: Munich Urban Planning agent: population vs scheduled transport and cycling coverage per district; planning dashboard on Dash Server
argument-hint: [question, optional]
---
Delegate this to the `urban-planning` subagent with the Agent tool (subagent_type "urban-planning").

Task for the agent, verbatim: $ARGUMENTS

If no task was given above, use the agent's default question:
"Which densely populated districts have lower scheduled public transport frequency or weaker cycling infrastructure? Build the planning dashboard."

Relay the agent's report in full: the answer, the ranked table, the SQL it showed, what the data cannot answer, and the Dash Server dashboard URL. The dashboard is always built on Dash Server through the dash-server MCP tools, never as an artifact, HTML page or inline chart. If the user says the dashboard already exists, tell the agent to refresh the existing app rather than create a new one.
