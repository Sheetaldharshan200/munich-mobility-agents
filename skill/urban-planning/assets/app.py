"""Munich Urban Planning - population density against scheduled transport and cycling supply per district.

Every figure comes from queries/*.sql, executed on Exasol through the server-side
'starter-kit' profile (read-only). Dash only renders.
"""
from dash import Dash, Input, Output, dcc, html
import plotly.graph_objects as go

from dash_server_exasol import has_error, load_rows
import munich_ui as ui

ACCENT = ui.PERSONA["planning"]
FLAG = ui.SLOTS[1]
# ordered from most to least separated from traffic: an ordinal ramp, one hue
PATH_GROUPS = ["Separated cycle path", "Cycle path", "Cycle street", "Cycle lane", "Shared path", "Footway, cycling allowed", "Other"]
PATH_COLORS = {**dict(zip(PATH_GROUPS[:6], ui.RAMP_BLUE[6:0:-1])), "Other": ui.MUTED}


def create_dash_app(server, url_base_pathname, metadata):
    app = Dash(__name__, server=server, routes_pathname_prefix="/", requests_pathname_prefix=url_base_pathname.rstrip("/") + "/",
               title=metadata.get("title", "Munich Urban Planning"), external_stylesheets=ui.STYLESHEETS)

    def q(path, params=None):
        return load_rows(server, metadata, __file__, path, params=params)

    table = ui.table("district-table", [
        {"name": "#", "id": "rank"}, {"name": "District", "id": "district"}, {"name": "Residents", "id": "population", "type": "numeric"},
        {"name": "Density /ha", "id": "density", "type": "numeric"}, {"name": "Stations", "id": "stations", "type": "numeric"},
        {"name": "Lines", "id": "lines", "type": "numeric"}, {"name": "Departures /1k", "id": "dep", "type": "numeric"},
        {"name": "Residents /station", "id": "rps", "type": "numeric"}, {"name": "Cycle-path m /1k", "id": "cyc", "type": "numeric"},
        {"name": "Coverage gap", "id": "gap", "type": "numeric"}, {"name": "Flag", "id": "flag"}],
        numeric_ids=("rank", "population", "density", "stations", "lines", "dep", "rps", "cyc", "gap"), highlight="gap", accent=FLAG)
    table.style_data_conditional.append({"if": {"filter_query": "{flag} != '-'"}, "backgroundColor": "#fff4ec"})

    app.layout = ui.page([
        dcc.Interval(id="boot", interval=200, max_intervals=1),
        html.Div(id="kpis"),
        ui.row([
            ui.card("Density against supply", ui.graph("scatter", 480),
                    "x: scheduled weekday departures per 1,000 residents · y: cycle-path metres per 1,000 residents · bubble size: residents per hectare. Orange = flagged."),
            ui.card("Departures per 1,000 residents, by mode", ui.graph("mode-bar", 480), "Night lines (under 1 % of departures) are left out."),
        ]),
        ui.block(ui.card("Districts ranked by coverage gap", html.Div([table, html.Div(id="table-error")]),
                         "Coverage gap = average supply rank (transit, cycling) minus density rank; positive means dense but under-served. "
                         "Flag = top third for density and bottom third for transit or cycling supply.", flex="1 1 100%")),
        ui.block(ui.card("Cycle-path type per district, metres per 1,000 residents", ui.graph("path-bar", 440),
                         "Darker = more separated from motor traffic.", flex="1 1 100%")),
        ui.notes("Method and data gaps", [
            "Transport supply: scheduled stop events on one representative weekday (first Wednesday on or after today inside the GTFS feed), summed over stops with in_munich = 1 per district.",
            "Cycling supply: metres of city-maintained cycle infrastructure per district (Dummy segments excluded).",
            "Indices run 0 to 100 across the 25 districts; ranks are 1 = highest.",
            "Not in the data: ridership, crowding, delays, cycle traffic away from the counters, planned infrastructure.",
        ]),
    ], eyebrow="Urban Planning", title="District coverage", accent=ACCENT,
        subtitle="Which densely populated districts have less scheduled public transport or weaker cycling infrastructure than their density warrants. "
                 "Scheduled service only: no passengers, delays or live traffic.")

    @app.callback(Output("kpis", "children"), Output("page-meta", "children"), Output("scatter", "figure"), Output("district-table", "data"),
                  Output("table-error", "children"), Output("mode-bar", "figure"), Output("path-bar", "figure"), Input("boot", "n_intervals"))
    def load(_n):
        k = q("queries/kpis.sql")
        if has_error(k):
            kpis, meta = ui.error_panel(k[0]["_error"]), ""
        else:
            k = ui.lower(k)[0]
            kpis = ui.tiles([
                ui.tile("Residents per station", ui.fmt(k["residents_per_station"]), "city-wide", ACCENT),
                ui.tile("Departures per 1,000 residents", ui.fmt(k["dep_per_1k"], 1), "scheduled weekday", ACCENT),
                ui.tile("Cycle-path m per 1,000 residents", ui.fmt(k["cycle_m_per_1k"]), "city-wide", ACCENT),
                ui.tile("Districts flagged", ui.fmt(k["districts_flagged"]), f"{ui.fmt(k['residents_in_flagged'])} residents", FLAG),
                ui.tile("Stops outside Munich", ui.fmt(k["stops_outside_munich"]), "excluded from every figure", ACCENT),
            ])
            meta = f"Reference weekday {k['ref_weekday']} · source: MUNICH_DATASET on Exasol, read-only"

        d = q("queries/districts.sql")
        if has_error(d):
            return kpis, meta, ui.empty("Query failed"), [], ui.error_panel(d[0]["_error"]), ui.empty(""), ui.empty("")
        d = ui.lower(d)
        rows = [{"rank": i, "district": r["district_name"], "population": int(ui.num(r["population"])), "density": int(ui.num(r["density_per_ha"])),
                 "stations": int(ui.num(r["stations"])), "lines": int(ui.num(r["n_lines"])), "dep": round(ui.num(r["dep_per_1k"]), 1),
                 "rps": int(ui.num(r["residents_per_station"])), "cyc": int(ui.num(r["cycle_m_per_1k"])), "gap": ui.num(r["coverage_gap"]),
                 "flag": r["flag_reason"] or "-"} for i, r in enumerate(d, start=1)]

        sc = go.Figure()
        for flagged, name, color in ((0, "Not flagged", ACCENT), (1, "Flagged", FLAG)):
            sub = [r for r in d if int(ui.num(r["flagged"])) == flagged]
            sc.add_trace(go.Scatter(
                x=[ui.num(r["dep_per_1k"]) for r in sub], y=[ui.num(r["cycle_m_per_1k"]) for r in sub], mode="markers+text", name=name,
                text=[r["district_name"].split("-")[0][:16] if flagged else "" for r in sub], textposition="top center", textfont={"size": 10, "color": ui.INK2},
                marker={"size": [10 + ui.num(r["density_per_ha"]) / 6 for r in sub], "color": color, "opacity": 0.85, "line": {"width": 2, "color": ui.SURFACE}},
                hovertext=[f"<b>{r['district_name']}</b><br>{ui.fmt(r['density_per_ha'])} residents per ha<br>{ui.fmt(r['dep_per_1k'], 1)} departures per 1,000<br>"
                           f"{ui.fmt(r['cycle_m_per_1k'])} m cycle path per 1,000<br>coverage gap {r['coverage_gap']}" + (f"<br>flag: {r['flag_reason']}" if r["flag_reason"] else "") for r in sub],
                hoverinfo="text"))
        ui.theme(sc, xaxis={"title": "Scheduled departures per 1,000 residents"}, yaxis={"title": "Cycle-path metres per 1,000 residents"})

        order = [r["district_name"] for r in d]
        pop = {r["district_name"]: ui.num(r["population"]) for r in d}
        m = q("queries/mode_split.sql")
        mb = go.Figure()
        if not has_error(m):
            m = ui.lower(m)
            for mode, color in ui.MODES.items():
                sub = [r for r in m if r["line_mode"] == mode]
                if sub:
                    mb.add_bar(y=[r["district_name"] for r in sub], x=[ui.num(r["departures"]) * 1000 / pop[r["district_name"]] for r in sub], name=mode,
                               orientation="h", marker={"color": color, "line": {"width": 1, "color": ui.SURFACE}},
                               hovertemplate="<b>%{y}</b><br>" + mode + ": %{x:,.0f} per 1,000 residents<extra></extra>")
        ui.theme(mb, barmode="stack", yaxis={"categoryorder": "array", "categoryarray": order[::-1], "automargin": True, "tickfont": {"size": 10}},
                 xaxis={"title": "Departures per 1,000 residents"}, bargap=0.3)

        p = q("queries/path_mix.sql")
        pb = go.Figure()
        if not has_error(p):
            p = ui.lower(p)
            for grp in PATH_GROUPS:
                sub = [r for r in p if r["path_group"] == grp]
                if sub:
                    pb.add_bar(x=[r["district_name"] for r in sub], y=[ui.num(r["metres"]) * 1000 / pop[r["district_name"]] for r in sub], name=grp,
                               marker={"color": PATH_COLORS[grp], "line": {"width": 1, "color": ui.SURFACE}},
                               hovertemplate="<b>%{x}</b><br>" + grp + ": %{y:,.0f} m per 1,000 residents<extra></extra>")
        ui.theme(pb, barmode="stack", xaxis={"categoryorder": "array", "categoryarray": order, "tickangle": -40, "automargin": True, "tickfont": {"size": 10}},
                 yaxis={"title": "Metres per 1,000 residents"}, legend={"y": 1.04})
        return kpis, meta, sc, rows, None, mb, pb

    return app
