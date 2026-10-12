"""Munich Mobility Operations - roadworks near busy stops, high-frequency lines and cycle paths.

Every figure comes from queries/*.sql, executed on Exasol through the server-side
'starter-kit' profile (read-only). Dash only renders.
"""
from dash import Dash, Input, Output, dcc, html
import plotly.graph_objects as go

from dash_server_exasol import has_error, load_rows
import munich_ui as ui

ACCENT = ui.PERSONA["ops"]
KIND_OPTIONS = [{"label": "All roadworks", "value": "all"},
                {"label": "Construction only (Baumaßnahme)", "value": "Baumaßnahme"},
                {"label": "Temporary no-parking only", "value": "Vorübergehendes Haltverbot"}]


def create_dash_app(server, url_base_pathname, metadata):
    app = Dash(__name__, server=server, routes_pathname_prefix="/", requests_pathname_prefix=url_base_pathname.rstrip("/") + "/",
               title=metadata.get("title", "Munich Mobility Operations"), external_stylesheets=ui.STYLESHEETS)

    def q(path, params=None):
        return load_rows(server, metadata, __file__, path, params=params)

    controls = html.Div([
        html.Div([html.Div("Horizon", style={"fontSize": "12px", "color": ui.MUTED, "marginBottom": "4px"}),
                  dcc.RadioItems(id="horizon", options=[{"label": f" {d} days", "value": d} for d in (7, 14, 28)], value=28, inline=True,
                                 inputStyle={"marginLeft": "12px"}, style={"fontSize": "13px"})]),
        html.Div([html.Div("Roadwork type", style={"fontSize": "12px", "color": ui.MUTED, "marginBottom": "4px"}),
                  dcc.Dropdown(id="kind", options=KIND_OPTIONS, value="all", clearable=False, style={"width": "300px", "fontSize": "13px"})]),
    ], style={"display": "flex", "gap": "28px", "flexWrap": "wrap", "alignItems": "flex-start", "margin": "0 0 16px"})

    worklist = ui.table("worklist", [
        {"name": "#", "id": "rank"}, {"name": "Roadwork", "id": "where"}, {"name": "District", "id": "district"},
        {"name": "Status", "id": "status"}, {"name": "Dates", "id": "dates"}, {"name": "Impact", "id": "impact"},
        {"name": "Nearest stop", "id": "nearest"}, {"name": "Departures ≤150 m", "id": "departures", "type": "numeric"},
        {"name": "High-frequency lines", "id": "hf"}, {"name": "Cycle-path m ≤100 m", "id": "cycle", "type": "numeric"},
        {"name": "Score", "id": "score", "type": "numeric"}],
        numeric_ids=("rank", "departures", "cycle", "score"), highlight="score", accent=ACCENT)

    app.layout = ui.page([
        dcc.Interval(id="boot", interval=200, max_intervals=1), dcc.Store(id="stops-store"), dcc.Store(id="zones-store"),
        controls,
        dcc.Loading(ui.tiles([]), id="kpis-wrap", type="dot", color=ui.MUTED), html.Div(id="kpis"),
        ui.row([
            ui.card("Disruption zones", ui.graph("map", 560, config={"scrollZoom": True}),
                    "Roadworks coloured by disruption score; stops with 100+ weekday departures as context. Scroll to zoom.", flex="2 1 560px"),
            ui.card("Disruption by district", ui.graph("district-bar", 560), "Sum of scores of all roadworks in the district.", flex="1 1 360px"),
        ]),
        ui.block(ui.card("Ranked worklist: top 25 disruption zones", html.Div([worklist, html.Div(id="worklist-error")]),
                         "Score = ln(1 + departures within 150 m) + cycle-path metres within 100 m ÷ 100 + 2 for a closure or lane loss + 1 for carriageway works, "
                         "scaled by days inside the next 28.", flex="1 1 100%")),
        ui.block(ui.card("High-frequency lines with roadworks beside their stops", ui.graph("lines-bar", 440),
                         "Lines with at least 100 trips per direction on the reference weekday. Bar = roadworks within 150 m of any of the line's stops.",
                         flex="1 1 100%")),
        ui.notes("Method and data gaps", [
            "Window: roadworks with end_date on or after today and start_date within the horizon. Works whose start is only recorded as 'more than a year ago' count as active.",
            "Departures: scheduled MVV stop events on one representative weekday (the first Wednesday on or after today inside the GTFS feed), including calendar exceptions; Munich stops only.",
            "Proximity: haversine distance from the roadwork centroid. Stops within 150 m, cycle-path segment midpoints within 100 m.",
            "Not in the data: passengers, delays, crowding, live traffic, diversion routes (GTFS shapes are empty), cycle volumes away from the counters.",
        ]),
    ], eyebrow="Mobility Operations", title="Roadworks disruption", accent=ACCENT,
        subtitle="Which current and planned roadworks collide with busy MVV stops, high-frequency lines and cycle paths over the next four weeks. "
                 "Scheduled service only: no passengers, delays or live traffic.")

    @app.callback(Output("stops-store", "data"), Input("boot", "n_intervals"))
    def load_stops(_n):
        rows = q("queries/stops_context.sql")
        return [] if has_error(rows) else [{"n": r["stop_name"], "lat": ui.num(r["lat"]), "lon": ui.num(r["lon"]), "d": int(ui.num(r["departures"]))}
                                           for r in ui.lower(rows)]

    @app.callback(Output("kpis", "children"), Output("zones-store", "data"), Output("worklist", "data"), Output("worklist-error", "children"),
                  Output("district-bar", "figure"), Output("lines-bar", "figure"), Output("page-meta", "children"),
                  Input("horizon", "value"), Input("kind", "value"))
    def refresh(horizon, kind):
        params = {"horizon": int(horizon or 28), "kind": kind or "all"}
        k = q("queries/kpis.sql", params)
        if has_error(k):
            kpis, meta = ui.error_panel(k[0]["_error"]), ""
        else:
            k = ui.lower(k)[0]
            kpis = ui.tiles([
                ui.tile("Roadworks in horizon", ui.fmt(k["roadworks_in_horizon"]), f"{ui.fmt(k['planned'])} planned, rest active", ACCENT),
                ui.tile("Within 150 m of a stop", ui.fmt(k["roadworks_near_stop"]), f"{ui.fmt(k['stops_affected'])} stops affected", ACCENT),
                ui.tile("Weekday departures ≤150 m", ui.fmt(k["departures_near_roadworks"]), "scheduled, distinct stops", ACCENT),
                ui.tile("High-frequency lines touched", f"{ui.fmt(k['hf_lines_affected'])} / {ui.fmt(k['hf_lines_total'])}", "100+ trips per direction", ACCENT),
                ui.tile("Cycle-path metres affected", ui.fmt(k["cycle_m_affected"]), f"{ui.fmt(k['roadworks_near_cycle'])} roadworks within 100 m", ACCENT),
            ])
            meta = f"Reference weekday {k['ref_weekday']} · source: MUNICH_DATASET on Exasol, read-only"

        z = q("queries/zones.sql", params)
        if has_error(z):
            return kpis, [], [], ui.error_panel(z[0]["_error"]), ui.empty("Query failed"), ui.empty("Query failed"), meta
        z = ui.lower(z)
        zones = [{"lat": ui.num(r["lat"]), "lon": ui.num(r["lon"]), "s": ui.num(r["score"]), "w": r["street"] or r["description"] or r["roadwork_id"],
                  "st": r["status"], "dep": int(ui.num(r["departures_150m"])), "cyc": int(ui.num(r["cycle_m_100m"])),
                  "stop": r["nearest_stop"] or "-", "hf": r["hf_lines"] or "-"} for r in z]
        work = []
        for i, r in enumerate(z[:25], start=1):
            work.append({"rank": i, "where": r["street"] or r["description"] or r["roadwork_id"], "district": r["district_name"] or "-",
                         "status": r["status"], "dates": f"{r['start_date'] or r['start_raw'] or ''} → {r['end_date']}",
                         "impact": (r["impact"] or r["affected_areas"] or r["kind"] or "")[:90],
                         "nearest": f"{r['nearest_stop']} ({int(ui.num(r['nearest_stop_m']))} m)" if r["nearest_stop"] else "-",
                         "departures": int(ui.num(r["departures_150m"])), "hf": r["hf_lines"] or "-",
                         "cycle": int(ui.num(r["cycle_m_100m"])), "score": round(ui.num(r["score"]), 2)})

        d = q("queries/districts.sql", params)
        if has_error(d):
            dfig = ui.empty("District query failed")
        else:
            d = sorted(ui.lower(d), key=lambda r: ui.num(r["total_score"]))
            dfig = go.Figure(go.Bar(
                x=[ui.num(r["total_score"]) for r in d], y=[r["district_name"] or "No district" for r in d], orientation="h",
                marker={"color": ACCENT}, name="Disruption",
                customdata=[[int(ui.num(r["roadworks"])), int(ui.num(r["near_stop"])), int(ui.num(r["closures"]))] for r in d],
                hovertemplate="<b>%{y}</b><br>total score %{x:,.0f}<br>%{customdata[0]} roadworks · %{customdata[1]} near a stop · %{customdata[2]} closures<extra></extra>"))
            ui.theme(dfig, showlegend=False, xaxis={"title": "Sum of disruption scores"}, yaxis={"automargin": True, "tickfont": {"size": 10}}, bargap=0.35)

        ln = q("queries/hf_lines.sql", params)
        if has_error(ln):
            lfig = ui.empty("Line query failed")
        else:
            ln = [r for r in ui.lower(ln) if r["line_mode"] in ui.MODES][:30]
            lfig = go.Figure()
            for mode, color in ui.MODES.items():
                sub = [r for r in ln if r["line_mode"] == mode]
                if sub:
                    lfig.add_bar(x=[r["line"] for r in sub], y=[ui.num(r["roadworks_150m"]) for r in sub], name=mode, marker={"color": color},
                                 customdata=[[int(ui.num(r["trips_per_dir"])), int(ui.num(r["stops_affected"]))] for r in sub],
                                 hovertemplate=f"<b>{mode} %{{x}}</b><br>%{{y}} roadworks within 150 m<br>%{{customdata[1]}} stops affected · %{{customdata[0]}} trips per direction<extra></extra>")
            ui.theme(lfig, xaxis={"type": "category", "categoryorder": "array", "categoryarray": [r["line"] for r in ln], "title": "Line"},
                     yaxis={"title": "Roadworks within 150 m"})
        return kpis, zones, work, None, dfig, lfig, meta

    @app.callback(Output("map", "figure"), Input("zones-store", "data"), Input("stops-store", "data"))
    def draw_map(zones, stops):
        fig = go.Figure()
        if stops:
            fig.add_trace(go.Scattermap(lat=[s["lat"] for s in stops], lon=[s["lon"] for s in stops], mode="markers", name="MVV stops (100+ departures)",
                                        marker={"size": [4 + min(s["d"], 1500) / 250 for s in stops], "color": ui.INK2, "opacity": 0.3},
                                        text=[f"{s['n']}<br>{s['d']:,} weekday departures" for s in stops], hoverinfo="text"))
        z = sorted(zones or [], key=lambda r: r["s"])
        if z:
            fig.add_trace(go.Scattermap(lat=[r["lat"] for r in z], lon=[r["lon"] for r in z], mode="markers", name="Roadworks, colour = score",
                                        marker={"size": [5 + r["s"] * 0.9 for r in z], "color": [r["s"] for r in z], "colorscale": ui.ramp_scale(ui.RAMP_ORANGE),
                                                "cmin": 0, "cmax": 16, "opacity": 0.9, "colorbar": {"title": {"text": "Score"}, "thickness": 10, "len": 0.5, "x": 0.99}},
                                        text=[f"<b>{r['w']}</b><br>{r['st']} · score {r['s']:.2f}<br>nearest stop {r['stop']}<br>{r['dep']:,} departures ≤150 m · {r['cyc']:,} m cycle path ≤100 m<br>high-frequency: {r['hf']}" for r in z],
                                        hoverinfo="text"))
        return ui.map_layout(fig, {"lat": 48.139, "lon": 11.575}, 11)

    return app
