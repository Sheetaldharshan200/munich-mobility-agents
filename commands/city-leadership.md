---
description: Munich City Leadership agent: evidence-based priorities across districts and corridors; executive dashboard on Dash Server
argument-hint: [question, optional]
---
Delegate this to the `city-leadership` subagent with the Agent tool (subagent_type "city-leadership").

Task for the agent, verbatim: $ARGUMENTS

If no task was given above, use the agent's default question:
"Where should Munich prioritise mobility planning or disruption mitigation based on the evidence from the other agents? Build the executive dashboard."

Relay the agent's report in full: the answer, the ranked table, the SQL it showed, what the data cannot answer, and the Dash Server dashboard URL. The dashboard is always built on Dash Server through the dash-server MCP tools, never as an artifact, HTML page or inline chart. If the user says the dashboard already exists, tell the agent to refresh the existing app rather than create a new one.
