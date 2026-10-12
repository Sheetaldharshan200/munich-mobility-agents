"""Munich City Leadership - one evidence-based priority ranking of districts and corridors.

Every figure comes from queries/*.sql, executed on Exasol through the server-side
'starter-kit' profile (read-only). The weights are a leadership choice and are
shown as sliders; the ranking recomputes in SQL when they move.
"""
from dash import Dash, Input, Output, dcc, html
import plotly.graph_objects as go

from dash_server_exasol import has_error, load_rows
import munich_ui as ui

ACCENT = ui.PERSONA["leadership"]
WEIGHTS = [("w_density", "Density", 0.30), ("w_gap", "Coverage gap", 0.30), ("w_disruption", "Roadwork disruption", 0.30), ("w_demand", "Cycling demand", 0.10)]
DRIVERS = [("density_idx", "w_density", "Density", ui.SLOTS[0]), ("coverage_gap_idx", "w_gap", "Coverage gap", ui.SLOTS[1]),
           ("disruption_idx", "w_disruption", "Roadwork disruption", ui.SLOTS[2]), ("demand_idx", "w_demand", "Cycling demand", ui.SLOTS[3])]


def create_dash_app(server, url_base_pathname, metadata):
    app = Dash(__name__, server=server, routes_pathname_prefix="/", requests_pathname_prefix=url_base_pathname.rstrip("/") + "/",
               title=metadata.get("title", "Munich Mobility Priorities"), external_stylesheets=ui.STYLESHEETS)

    def q(path, params=None):
        return load_rows(server, metadata, __file__, path, params=params)

    sliders = html.Div([
        *[html.Div([html.Div(label, style={"fontSize": "12px", "color": ui.INK2, "fontWeight": 500}),
                    dcc.Slider(id=key, min=0, max=1, step=0.05, value=default, marks={0: "0", 0.5: "0.5", 1: "1"}, tooltip={"placement": "bottom"})],
                   style={"flex": "1 1 170px", "minWidth": "160px"}) for key, label, default in WEIGHTS],
        html.Div(id="weight-note", style={"fontSize": "12px", "color": ui.MUTED, "alignSelf": "flex-end", "flex": "1 1 240px"}),
    ], style={**ui.CARD, "display": "flex", "gap": "22px", "flexWrap": "wrap", "margin": "0 0 14px", "padding": "12px 18px 6px"})

    table = ui.table("priority-table", [
        {"name": "#", "id": "rank"}, {"name": "District", "id": "district"}, {"name": "Residents", "id": "population", "type": "numeric"},
        {"name": "Density /ha", "id": "density", "type": "numeric"}, {"name": "Departures /1k", "id": "dep", "type": "numeric"},
        {"name": "Cycle m /1k", "id": "cyc", "type": "numeric"}, {"name": "Roadworks, 28 d", "id": "rw", "type": "numeric"},
        {"name": "Disruption", "id": "dis", "type": "numeric"}, {"name": "Density idx", "id": "i1", "type": "numeric"},
        {"name": "Gap idx", "id": "i2", "type": "numeric"}, {"name": "Disruption idx", "id": "i3", "type": "numeric"},
        {"name": "Demand idx", "id": "i4", "type": "numeric"}, {"name": "Priority", "id": "prio", "type": "numeric"}, {"name": "Planning flag", "id": "flag"}],
        numeric_ids=("rank", "population", "density", "dep", "cyc", "rw", "dis", "i1", "i2", "i3", "i4", "prio"), highlight="prio", accent=ACCENT)
    table.style_data_conditional.append({"if": {"filter_query": "{rank} <= 5"}, "backgroundColor": "#f3f1fb"})

    corridors = ui.table("corridor-table", [
        {"name": "Roadwork", "id": "where"}, {"name": "District (rank)", "id": "district"}, {"name": "Dates", "id": "dates"}, {"name": "Impact", "id": "impact"},
        {"name": "Nearest stop", "id": "stop"}, {"name": "Departures ≤150 m", "id": "dep", "type": "numeric"},
        {"name": "Cycle m ≤100 m", "id": "cyc", "type": "numeric"}, {"name": "Score", "id": "score", "type": "numeric"}],
        numeric_ids=("dep", "cyc", "score"), highlight="score", accent=ui.PERSONA["ops"])

    app.layout = ui.page([
        sliders,
        html.Div(id="kpis"),
        ui.row([
            ui.card("Priority by district", ui.graph("map", 480), "Number = rank. Darker and larger = higher priority.", flex="1 1 440px"),
            ui.card("What drives each district's priority", ui.graph("drivers", 480), "Weighted contribution of each index, top 12 districts.", flex="1 1 440px"),
        ]),
        ui.block(ui.card("Priority ranking with its evidence", html.Div([table, html.Div(id="table-error")]),
                         "Indices run 0 to 100 across the 25 districts. Gap idx = 100 − average of the transit and cycling supply indices. "
                         "Disruption = sum of the operations disruption scores of the district's roadworks over the next 28 days. "
                         "Demand idx comes from the bicycle counters, so it is 0 where no counter exists.", flex="1 1 100%")),
        ui.block(ui.card("Priority corridors: top disruption zones inside the five priority districts", corridors, flex="1 1 100%")),
        ui.notes("What we do not know", [
            "Scheduled service is not actual service: no ridership, delays or crowding.",
            "Five bicycle counters with data, so cycling demand is unknown in 21 districts and gets a weight of 0.10 by default.",
            "Roadworks are a four-week horizon from the download date; severity is parsed from German free text.",
            "Population is a point-in-time snapshot from the city portal.",
        ]),
    ], eyebrow="City Leadership", title="Mobility priorities", accent=ACCENT,
        subtitle="Where planning and disruption-mitigation effort goes first: one ranking from density, coverage gap, roadwork disruption and cycling demand. "
                 "The weights are a leadership choice, not a fact. Move them and the ranking recomputes.")

    @app.callback(Output("kpis", "children"), Output("weight-note", "children"), Output("page-meta", "children"), Output("map", "figure"),
                  Output("drivers", "figure"), Output("priority-table", "data"), Output("table-error", "children"), Output("corridor-table", "data"),
                  *[Input(key, "value") for key, _, _ in WEIGHTS])
    def refresh(w_density, w_gap, w_disruption, w_demand):
        ws = {"w_density": w_density or 0, "w_gap": w_gap or 0, "w_disruption": w_disruption or 0, "w_demand": w_demand or 0}
        total = sum(ws.values()) or 1
        params = {k: round(v / total, 4) for k, v in ws.items()}
        params.update({"horizon": 28, "kind": "all"})
        note = "Weights normalised to " + ", ".join(f"{label} {params[key]:.2f}" for key, label, _ in WEIGHTS)

        k = q("queries/kpis.sql", params)
        if has_error(k):
            kpis, meta = ui.error_panel(k[0]["_error"]), ""
        else:
            k = ui.lower(k)[0]
            kpis = ui.tiles([
                ui.tile("Districts flagged for planning", ui.fmt(k["districts_flagged"]), f"{ui.fmt(k['residents_in_flagged'])} residents", ACCENT),
                ui.tile("Residents in the top-5 priority districts", ui.fmt(k["residents_in_top5"]), "", ACCENT),
                ui.tile("Departures within 150 m of roadworks", ui.fmt(k["departures_near_roadworks"]), f"{ui.fmt(k['roadworks_in_horizon'])} roadworks in the next 28 days", ACCENT),
                ui.tile("Cycle-path m per 1,000 residents", ui.fmt(k["cycle_m_per_1k_city"]), "city-wide", ACCENT),
            ])
            meta = f"Reference weekday {k['ref_weekday']} · source: MUNICH_DATASET on Exasol, read-only"

        p = q("queries/priorities.sql", params)
        if has_error(p):
            return kpis, note, meta, ui.empty("Query failed"), ui.empty(""), [], ui.error_panel(p[0]["_error"]), []
        p = ui.lower(p)
        rows = [{"rank": int(ui.num(r["priority_rank"])), "district": r["district_name"], "population": int(ui.num(r["population"])),
                 "density": int(ui.num(r["density_per_ha"])), "dep": round(ui.num(r["dep_per_1k"]), 1), "cyc": int(ui.num(r["cycle_m_per_1k"])),
                 "rw": int(ui.num(r["roadworks"])), "dis": round(ui.num(r["disruption"])), "i1": int(ui.num(r["density_idx"])), "i2": int(ui.num(r["coverage_gap_idx"])),
                 "i3": int(ui.num(r["disruption_idx"])), "i4": int(ui.num(r["demand_idx"])), "prio": ui.num(r["priority"]), "flag": r["flag_reason"] or "-"} for r in p]

        geo = {r["district_no"]: r for r in ui.lower(q("queries/district_geo.sql")) if not r.get("_error")}
        pts = [r for r in p if r["district_no"] in geo]
        mp = go.Figure(go.Scattermap(
            lat=[ui.num(geo[r["district_no"]]["lat"]) for r in pts], lon=[ui.num(geo[r["district_no"]]["lon"]) for r in pts], mode="markers+text",
            text=[str(int(ui.num(r["priority_rank"]))) for r in pts], textfont={"color": "#ffffff", "size": 11},
            marker={"size": [16 + ui.num(r["priority"]) / 3 for r in pts], "color": [ui.num(r["priority"]) for r in pts], "colorscale": ui.ramp_scale(ui.RAMP_VIOLET),
                    "cmin": 0, "cmax": 100, "opacity": 0.92, "colorbar": {"title": {"text": "Priority"}, "thickness": 10, "len": 0.5, "x": 0.99}},
            hovertext=[f"<b>#{int(ui.num(r['priority_rank']))} {r['district_name']}</b><br>priority {r['priority']}<br>density {int(ui.num(r['density_idx']))} · gap {int(ui.num(r['coverage_gap_idx']))} · "
                       f"disruption {int(ui.num(r['disruption_idx']))} · demand {int(ui.num(r['demand_idx']))}" for r in pts], hoverinfo="text"))
        ui.map_layout(mp, {"lat": 48.139, "lon": 11.56}, 10.3)
        mp.update_layout(showlegend=False)

        top = p[:12][::-1]
        dr = go.Figure()
        for key, wkey, label, color in DRIVERS:
            dr.add_bar(y=[r["district_name"] for r in top], x=[ui.num(r[key]) * params[wkey] for r in top], name=label, orientation="h",
                       marker={"color": color, "line": {"width": 1, "color": ui.SURFACE}}, hovertemplate="<b>%{y}</b><br>" + label + ": %{x:.1f} points<extra></extra>")
        ui.theme(dr, barmode="stack", xaxis={"title": "Priority points"}, yaxis={"automargin": True, "tickfont": {"size": 10}}, bargap=0.32)

        c = q("queries/corridors.sql", params)
        crows = [] if has_error(c) else [
            {"where": r["street"] or r["roadwork_id"], "district": f"{r['district_name']} (#{int(ui.num(r['district_rank']))})",
             "dates": f"{r['start_date'] or 'before 2025'} → {r['end_date']}", "impact": (r["impact"] or "")[:80],
             "stop": f"{r['nearest_stop']} ({int(ui.num(r['nearest_stop_m']))} m)" if r["nearest_stop"] else "-",
             "dep": int(ui.num(r["departures_150m"])), "cyc": int(ui.num(r["cycle_m_100m"])), "score": ui.num(r["score"])} for r in ui.lower(c)]
        return kpis, note, meta, mp, dr, rows, None, crows

    return app
