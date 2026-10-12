"""Skeleton for a Munich persona dashboard on Dash Server.

Copy this to app.py in the app workspace, keep the structure, replace every TODO.
The shared look (tiles, cards, chart theme, tables, maps) is in munich_ui.py; you
write the queries and decide what each chart says.

Rules the host enforces: a create_dash_app factory, callbacks registered on `app`,
no query at import time, every query in queries/*.sql through load_rows.
"""
from dash import Dash, Input, Output, dcc, html
import plotly.graph_objects as go

from dash_server_exasol import has_error, load_rows
import munich_ui as ui

ACCENT = ui.PERSONA["ops"]  # TODO: "ops" | "planning" | "sustainability" | "leadership"


def create_dash_app(server, url_base_pathname, metadata):
    app = Dash(__name__, server=server, routes_pathname_prefix="/",
               requests_pathname_prefix=url_base_pathname.rstrip("/") + "/",
               title=metadata.get("title", "Munich dashboard"), external_stylesheets=ui.STYLESHEETS)

    def q(path, params=None):
        return load_rows(server, metadata, __file__, path, params=params)

    # TODO: controls the persona needs (a horizon, a filter, weight sliders), or none.
    controls = html.Div([
        html.Div([html.Div("Horizon", style={"fontSize": "12px", "color": ui.MUTED, "marginBottom": "4px"}),
                  dcc.RadioItems(id="horizon", options=[{"label": f" {d} days", "value": d} for d in (7, 14, 28)],
                                 value=28, inline=True, inputStyle={"marginLeft": "12px"}, style={"fontSize": "13px"})]),
    ], style={"display": "flex", "gap": "28px", "flexWrap": "wrap", "margin": "0 0 16px"})

    ranking = ui.table("ranking", [
        {"name": "#", "id": "rank"}, {"name": "Name", "id": "name"},  # TODO: columns of the ranked table
        {"name": "Value", "id": "value", "type": "numeric"}, {"name": "Score", "id": "score", "type": "numeric"}],
        numeric_ids=("rank", "value", "score"), highlight="score", accent=ACCENT)

    app.layout = ui.page([
        dcc.Interval(id="boot", interval=200, max_intervals=1),   # first load; remove when controls drive the callback
        controls,
        html.Div(id="kpis"),
        ui.row([
            ui.card("TODO chart title", ui.graph("map", 520, config={"scrollZoom": True}), "TODO one line on what the map shows", flex="2 1 560px"),
            ui.card("TODO chart title", ui.graph("bar", 520), "TODO one line on what the bar shows", flex="1 1 360px"),
        ]),
        ui.block(ui.card("TODO ranked table title", html.Div([ranking, html.Div(id="ranking-error")]),
                         "TODO the formula behind the score, in one sentence", flex="1 1 100%")),
        ui.notes("Method and data gaps", [
            "TODO how the numbers were computed (window, reference weekday, distance rule)",
            "TODO what the data cannot answer",
        ]),
    ], eyebrow="TODO persona", title="TODO title", accent=ACCENT,
        subtitle="TODO the question this page answers, in one sentence, plus the main caveat.")

    @app.callback(Output("kpis", "children"), Output("ranking", "data"), Output("ranking-error", "children"),
                  Output("map", "figure"), Output("bar", "figure"), Output("page-meta", "children"),
                  Input("horizon", "value"))
    def refresh(horizon):
        params = {"horizon": int(horizon or 28)}            # placeholders are pyexasol style: {horizon!d}, {name!s}

        k = q("queries/kpis.sql", params)                   # TODO: one row of headline numbers
        if has_error(k):
            return ui.error_panel(k[0]["_error"]), [], None, ui.empty("Query failed"), ui.empty("Query failed"), ""
        k = ui.lower(k)[0]
        kpis = ui.tiles([
            ui.tile("TODO label", ui.fmt(k["todo_column"]), "TODO note", ACCENT),
        ])
        meta = f"Reference weekday {k.get('ref_weekday', '')} · source: MUNICH_DATASET on Exasol, read-only"

        r = q("queries/ranking.sql", params)                # TODO: the ranked rows, ordered by score
        if has_error(r):
            return kpis, [], ui.error_panel(r[0]["_error"]), ui.empty("Query failed"), ui.empty("Query failed"), meta
        r = ui.lower(r)
        rows = [{"rank": i, "name": x["name"], "value": ui.num(x["value"]), "score": round(ui.num(x["score"]), 2)}
                for i, x in enumerate(r[:25], start=1)]

        # map: one trace per entity type; colour = magnitude on a one-hue ramp
        mp = go.Figure(go.Scattermap(
            lat=[ui.num(x["lat"]) for x in r], lon=[ui.num(x["lon"]) for x in r], mode="markers", name="TODO",
            marker={"size": [6 + ui.num(x["score"]) for x in r], "color": [ui.num(x["score"]) for x in r],
                    "colorscale": ui.ramp_scale(ui.RAMP_ORANGE), "colorbar": {"title": {"text": "Score"}, "thickness": 10, "len": 0.5}},
            text=[f"<b>{x['name']}</b><br>score {ui.num(x['score']):.2f}" for x in r], hoverinfo="text"))
        ui.map_layout(mp, {"lat": 48.139, "lon": 11.575}, 11)

        # bar: single series in the persona accent, horizontal, sorted
        top = sorted(r[:15], key=lambda x: ui.num(x["score"]))
        bar = go.Figure(go.Bar(x=[ui.num(x["score"]) for x in top], y=[x["name"] for x in top], orientation="h",
                               marker={"color": ACCENT}, hovertemplate="<b>%{y}</b><br>%{x:.2f}<extra></extra>"))
        ui.theme(bar, showlegend=False, xaxis={"title": "TODO axis title"}, yaxis={"automargin": True})
        return kpis, rows, None, mp, bar, meta

    return app
