---
description: Munich Sustainability agent: cycling demand, weather and seasonality at the six counters; cycling demand dashboard on Dash Server
argument-hint: [question, optional]
---
Delegate this to the `sustainability` subagent with the Agent tool (subagent_type "sustainability").

Task for the agent, verbatim: $ARGUMENTS

If no task was given above, use the agent's default question:
"How do weather, seasonality and location affect cycling demand across Munich? Build the cycling demand dashboard."

Relay the agent's report in full: the answer, the ranked table, the SQL it showed, what the data cannot answer, and the Dash Server dashboard URL. The dashboard is always built on Dash Server through the dash-server MCP tools, never as an artifact, HTML page or inline chart. If the user says the dashboard already exists, tell the agent to refresh the existing app rather than create a new one.
