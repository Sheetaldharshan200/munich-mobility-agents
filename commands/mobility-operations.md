---
description: Munich Mobility Operations agent: roadworks near stops, routes and cycling corridors; disruption dashboard on Dash Server
argument-hint: [question, optional]
---
Delegate this to the `mobility-operations` subagent with the Agent tool (subagent_type "mobility-operations").

Task for the agent, verbatim: $ARGUMENTS

If no task was given above, use the agent's default question:
"Which current or planned roadworks are close to important public transport stops, high-frequency routes or busy cycling corridors? Build the disruption dashboard."

Relay the agent's report in full: the answer, the ranked table, the SQL it showed, what the data cannot answer, and the Dash Server dashboard URL. The dashboard is always built on Dash Server through the dash-server MCP tools, never as an artifact, HTML page or inline chart. If the user says the dashboard already exists, tell the agent to refresh the existing app rather than create a new one.
