# Talk track (extracted from 'Munich Data Geeks_Talk tracks-2.docx')


### Talk Options


#### Option 1: One Retailer, Four Data Agents: Building Agentic Data Intelligence with Exasol Personal

A fictional retailer uses Exasol as a shared data foundation for merchandising, supply chain, marketing, and leadership.

Each department has a specialized data agent that answers real business questions using the same governed data:

- Merchandising: Which products have low sell-through and should be discounted?
- Supply chain: Which stores are at risk of stockouts?
- Marketing: Which promotions produced genuine incremental sales?
- Leadership: Why did profitability change, and what should we prioritize?
During the demo, each agent generates transparent SQL, analyzes the results, and creates a persona-specific view using Dash Server. The leadership agent then connects insights from across departments into one executive view.

Best fit: Strongest combination of technical depth, business relevance, agentic AI, analytics, and visual storytelling.


#### Option 2: Munich in Motion: What Open Data Reveals About How the City Moves

Use Munich mobility, weather, events, and public transport data to investigate how the city moves.

The demo would:

- Load and combine several public datasets.
- Investigate congestion, unusual travel patterns, or changes in demand.
- Use SQL to identify trends and anomalies.
- Present the findings through an interactive dashboard.
- Give attendees a reproducible example they can explore at home.
Best fit: Strong local relevance and a community-first introduction to Exasol Personal.


#### Option 3: From Six Hours to Six Minutes: Scaling Analytics in the Real World

Present an approved customer or industry story showing how increasing data volumes, complex queries, and growing concurrency created an analytics bottleneck.

The demo would:

- Recreate a representative analytical workload.
- Show where the original bottleneck occurred.
- Inspect the query and architecture.
- Run the improved workload using Exasol.
- Explain the engineering decisions and trade-offs.
Best fit: Strong production credibility. This option depends on customer participation, approved performance claims, and access to a representative dataset.


## Recommendation


### One Retailer. Four Personas. One Data Foundation.

We recommend leading with:

One Retailer, Four Data Agents: Building Agentic Data Intelligence with Exasol Personal

This concept presents Exasol Personal as the foundation for prototyping agentic data intelligence across an organization.

The core message is:

Agentic data intelligence is not about placing several chatbots on top of disconnected data. It is about giving specialized agents access to one governed data foundation, with consistent metrics, transparent SQL, controlled access, and visible outcomes.


### Recommended Demo Flow


#### 1. Merchandising

The merchandising agent identifies products with low sell-through and recommends where targeted markdowns could release inventory without unnecessarily reducing margin.


#### 2. Supply Chain

The supply-chain agent combines inventory and sales velocity to identify stores at risk of stockouts and prioritizes replenishment.


#### 3. Marketing

The marketing agent evaluates promotional lift and distinguishes incremental sales from demand that would have occurred without the campaign.


#### 4. Leadership

The leadership agent investigates why profitability changed, connects findings across departments, and produces an executive Dash Server view with recommended priorities.


### What the Audience Will See

- One retail data model covering sales, inventory, products, customers, stores, promotions, and returns.
- Natural-language questions translated into inspectable SQL.
- Traceable analytical results rather than unsupported AI-generated answers.
- Persona-specific dashboards created from the same governed data.
- Read-only access and a deliberately restricted or ambiguous question to demonstrate guardrails.
- A complete workflow that attendees can reproduce using Exasol Personal.

### Why This Option Stands Out

- It tells one coherent organizational story rather than demonstrating isolated product features.
- It combines agentic AI, data engineering, analytics, SQL, governance, and dashboards.
- It provides relevant takeaways for engineers, analysts, data scientists, and students.
- Dash Server makes the results immediately visible.
- The different personas create natural transitions and keep the live demo engaging.
- It positions Exasol as the trusted data foundation without turning the session into a product pitch.

## Munich Data Geeks Meetup


### Updated Talk Concept and Recommendation


### Recommended Talk


#### Munich in Motion: Four Data Agents Planning for a Growing City

Subtitle:How Exasol Personal can provide a shared foundation for agentic data intelligence across mobility operations, urban planning, sustainability and city leadership.


### Talk Overview

Munich’s continued growth creates increasingly connected mobility challenges. Public transport coverage, cycling demand, roadworks, population density and infrastructure planning cannot be considered independently.

This talk will demonstrate how publicly available Munich data can be brought together in Exasol Personal and used by specialized data agents serving different organizational personas.

Each agent works with the same governed data foundation, generates transparent SQL and presents its findings through persona-specific Dash Server views.

The purpose is not to present a fictional real-time control centre. It is to demonstrate how agentic data intelligence can support mobility planning, disruption analysis and evidence-based decision-making.


### Public Datasets


#### 1. Munich Bicycle Counts 2026

Source: Munich Open Data Portal

The dataset contains:

- Fifteen-minute bicycle counts from six locations
- Daily totals
- Minimum and maximum temperature
- Rainfall
- Cloud cover
- Sunshine duration
The data is published monthly and can be used to identify cycling patterns, seasonal changes, anomalies and the influence of weather.


#### 2. MVV Public Transport Schedules

Source: MVV Developer Area

The GTFS dataset contains:

- Public transport stops
- Routes and transport modes
- Planned trips
- Stop sequences
- Scheduled arrival and departure times
- Geographic route information
The full MVV feed covers regional rail, S-Bahn, U-Bahn, tram and bus services.

This is scheduled transport data. It does not contain actual passenger numbers, delays or crowding.


#### 3. Current and Planned Roadworks  - Validated

Source: Munich Roadworks Open Data

The dataset contains current and planned roadworks and temporary restrictions affecting driving, walking and parking over the following four weeks.

It is available in GeoJSON and CSV formats and is updated daily.


#### 4. Population by Munich District

Source: Population in Munich Districts

The dataset provides population and area information for Munich’s 25 districts.

It can be used to compare population demand with scheduled public transport coverage and mobility infrastructure.


#### 5. Munich District Boundaries - Validated

Source: Munich District Boundaries

The dataset provides the geographic boundaries of Munich’s 25 districts in GeoJSON and CSV formats.

It enables spatial joins, district-level comparisons and map-based Dash Server views.


#### 6. Munich Cycling Infrastructure

Source: Munich Cycling Infrastructure

The dataset contains cycling infrastructure maintained by the City of Munich, including information about different types of cycle routes.

It can be used to compare observed cycling demand with available infrastructure.


#### Optional Historical Dataset: MVG Bike Trips

Source: Historical MVG Bike Trips

This dataset contains anonymised MVG bike journeys from 2015 to September 2025, including:

- Start and end times
- Start and end coordinates
- Station-based and free-floating journeys
- Station names where applicable
The MVG-Rad service ended in September 2025, so this should only be used for historical analysis.


### Persona-Based Demo


#### 1. Mobility Operations Agent

Question:Which current or planned roadworks are close to important public transport stops, high-frequency routes or busy cycling corridors?

Demo output:

- Roadworks mapped against transport stops and cycling locations
- Potential disruption zones
- Routes and areas requiring further operational review
- Dash Server disruption view

#### 2. Urban Planning Agent

Question:Which densely populated districts appear to have lower scheduled public transport frequency or weaker cycling infrastructure?

Demo output:

- Population compared with scheduled service frequency
- Stops and routes per district
- Cycling infrastructure coverage
- Districts that may require further planning analysis

#### 3. Sustainability Agent

Question:How do weather, seasonality and location affect cycling demand across Munich?

Demo output:

- Cycling patterns by location and time
- Weather sensitivity
- Weekday and weekend differences
- Locations that recover fastest after poor weather
- Cycling demand dashboard

#### 4. City Leadership Agent

Question:Where should Munich prioritize mobility planning or disruption mitigation based on the available evidence?

Demo output:

- Consolidated view across population, transport, cycling and roadworks
- Priority districts and corridors
- Supporting evidence behind each recommendation
- Executive Dash Server view

### What the Audience Will See

- CSV, and JSON data loaded into Exasol Personal Local
- Multiple public datasets joined into one analytical model
- Natural-language questions translated into inspectable SQL
- Persona-specific data agents working with the same governed foundation
- Dash Server views generated for different personas
- A reproducible prototype that attendees can explore themselves

### Core Message

Agentic data intelligence is not about placing multiple chatbots on top of disconnected datasets. It is about giving specialized agents controlled access to one governed data foundation, with consistent metrics, transparent SQL and evidence that users can inspect.


### Why This Concept Works

- It combines the organizational storytelling of the multi-persona concept with the local relevance of Munich mobility.
- It uses real public data rather than an entirely fictional business dataset.
- It provides meaningful technical content for engineers, analysts and data scientists.
- It gives students and developers a use case they can reproduce using Exasol Personal.
- It naturally demonstrates data ingestion, SQL, spatial analysis, agents, governance and dashboards.
- Exasol remains an enabling foundation rather than becoming the subject of a product presentation.

### Important Positioning

The talk should not claim to demonstrate a live Munich mobility control centre.

The available MVV data contains scheduled services, not actual passenger counts, delays or crowding. We have also not identified verified public datasets for real-time vehicle congestion or comprehensive Munich event impact.

The talk should therefore focus on:

- Mobility planning
- Scheduled service coverage
- Disruption analysis
- Cycling demand
- Infrastructure assessment
- Evidence-based prioritization
Any synthetic operational data used in the demonstration must be clearly identified as synthetic.

Exasol Personal should be positioned as the single-user environment used to prototype and reproduce the architecture. The conclusion can explain how the same pattern extends to an enterprise deployment supporting multiple agents, applications and users.


### Suggested 35-Minute Flow

- 5 minutes: Munich’s growth and mobility-planning challenge
- 5 minutes: Public datasets and shared Exasol architecture
- 20 minutes: Four-persona live demonstration
- 5 minutes: Governance, limitations and how attendees can reproduce the prototype

### Next Steps

- Download and profile the identified public datasets.
- Confirm the geographic and time coverage of each source.
- Select the exact questions each persona will ask.
- Define the common Exasol data model.
- Create the four Dash Server views.
- Decide whether historical MVG bike journeys should be included.
- Rehearse the demo using a fixed data snapshot to reduce live-event risk.
