"""Munich Sustainability - cycling demand against weather, season and location at the permanent counters.

Every figure comes from queries/*.sql, executed on Exasol through the server-side
'starter-kit' profile (read-only). Dash only renders.
"""
from dash import Dash, Input, Output, dcc, html
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dash_server_exasol import has_error, load_rows
import munich_ui as ui

ACCENT = ui.PERSONA["sustainability"]
DRY, RAINY = ui.SLOTS[2], ui.SLOTS[0]        # aqua / blue: adjacent pair validated
WEEKDAY, WEEKEND = ui.SLOTS[0], ui.SLOTS[1]  # blue / orange
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def create_dash_app(server, url_base_pathname, metadata):
    app = Dash(__name__, server=server, routes_pathname_prefix="/", requests_pathname_prefix=url_base_pathname.rstrip("/") + "/",
               title=metadata.get("title", "Munich Cycling Demand"), external_stylesheets=ui.STYLESHEETS)

    def q(path, params=None):
        return load_rows(server, metadata, __file__, path, params=params)

    table = ui.table("counter-table", [
        {"name": "Counter", "id": "name"}, {"name": "Days", "id": "days", "type": "numeric"}, {"name": "Avg daily", "id": "avg", "type": "numeric"},
        {"name": "Weekday", "id": "wd", "type": "numeric"}, {"name": "Weekend", "id": "we", "type": "numeric"},
        {"name": "Weekday ÷ weekend", "id": "ratio", "type": "numeric"}, {"name": "Dry days", "id": "dry", "type": "numeric"},
        {"name": "Rainy days", "id": "rainy", "type": "numeric"}, {"name": "Rain penalty", "id": "pen", "type": "numeric"},
        {"name": "Cyclists per +1 °C", "id": "deg", "type": "numeric"}, {"name": "Sunshine corr.", "id": "sun", "type": "numeric"},
        {"name": "Recovery ratio", "id": "rec", "type": "numeric"}, {"name": "Recovery rank", "id": "rrank", "type": "numeric"}],
        numeric_ids=("days", "avg", "wd", "we", "ratio", "dry", "rainy", "pen", "deg", "sun", "rec", "rrank"), highlight="pen", accent=ui.SLOTS[1], page_size=10)

    app.layout = ui.page([
        dcc.Interval(id="boot", interval=200, max_intervals=1), dcc.Store(id="heat-store"),
        html.Div(id="kpis"),
        ui.block(ui.card("Daily cyclists per counter, with the day's rain", ui.graph("daily", 460),
                         "Top: cyclists per day. Bottom: rain in mm on the same days. One axis each, so the eye compares shape, not height.", flex="1 1 100%")),
        ui.row([
            ui.card("Dry days against rainy days", ui.graph("rain-bar", 340), "Rainy = more than 1 mm.", flex="1 1 320px"),
            ui.card("Cyclists by maximum temperature, dry days", ui.graph("temp-line", 340), "5 °C bands.", flex="1 1 320px"),
            ui.card("Weekday against weekend", ui.graph("wk-bar", 340), "A high ratio is a commuter counter.", flex="1 1 320px"),
        ]),
        ui.block(ui.card("Counter comparison", html.Div([table, html.Div(id="table-error")]),
                         "Rain penalty = 1 − rainy-day average ÷ dry-day average. Recovery ratio = first dry day after rain ÷ trailing 7-day dry average; "
                         "1.0 means fully back to normal. Cyclists per +1 °C is the regression slope on maximum temperature.", flex="1 1 100%")),
        ui.row([
            ui.card("Hour by weekday", html.Div([dcc.Dropdown(id="heat-counter", clearable=False, style={"width": "320px", "fontSize": "13px", "marginBottom": "6px"}),
                                                 ui.graph("heatmap", 340)]), "Average cyclists per hour from the 15-minute counts.", flex="2 1 520px"),
            ui.card("Counter locations", ui.graph("map", 400), "Marker size = average daily cyclists.", flex="1 1 320px"),
        ]),
        ui.block(ui.card("Monthly trend", ui.graph("monthly", 320), "Average daily cyclists per month. Hover for that month's temperature and rain.", flex="1 1 100%")),
        ui.notes("Method and data gaps", [
            "Daily counts from the city's permanent bicycle counters, January to July 2026, joined to the weather of the day. Arnulf has data to the end of April only.",
            "Five counters with data are not the whole city: they say how demand reacts to weather and season where they stand, not how many people cycle in Munich.",
            "Recovery ratio needs a dry day right after a rainy one and at least one dry day in the previous week.",
        ]),
    ], eyebrow="Sustainability", title="Cycling demand", accent=ACCENT,
        subtitle="How weather, season and location shape cycling demand at Munich's permanent bicycle counters, to time campaigns and target weather-resilient infrastructure.")

    @app.callback(Output("kpis", "children"), Output("page-meta", "children"), Output("daily", "figure"), Output("rain-bar", "figure"),
                  Output("temp-line", "figure"), Output("wk-bar", "figure"), Output("counter-table", "data"), Output("table-error", "children"),
                  Output("map", "figure"), Output("monthly", "figure"), Output("heat-store", "data"), Output("heat-counter", "options"),
                  Output("heat-counter", "value"), Input("boot", "n_intervals"))
    def load(_n):
        k = q("queries/kpis.sql")
        if has_error(k):
            kpis, meta = ui.error_panel(k[0]["_error"]), ""
        else:
            k = ui.lower(k)[0]
            kpis = ui.tiles([
                ui.tile("Cyclists counted", ui.fmt(k["cyclists_counted"]), f"{k['first_day']} to {k['last_day']}, {ui.fmt(k['counters'])} counters", ACCENT),
                ui.tile("Busiest counter", ui.fmt(k["busiest_avg_daily"]), f"cyclists per day at {k['busiest_counter']}", ACCENT),
                ui.tile("Rain penalty", f"{ui.num(k['avg_rain_penalty']) * 100:.0f} %", "fewer cyclists on a rainy day, average of counters", ACCENT),
                ui.tile("Rainy-day volume", f"{ui.num(k['rainy_vs_dry_ratio']) * 100:.0f} %", "of a dry day, all counters together", ACCENT),
            ])
            meta = "Source: MUNICH_DATASET on Exasol, read-only"

        c = q("queries/counters.sql")
        if has_error(c):
            e = ui.empty("Query failed")
            return kpis, meta, e, e, e, e, [], ui.error_panel(c[0]["_error"]), e, e, [], [], None
        c = ui.lower(c)
        colors = {r["station"]: ui.SLOTS[i] for i, r in enumerate(c)}
        names = {r["station"]: r["station_name"] for r in c}
        rows = [{"name": r["station_name"], "days": int(ui.num(r["days"])), "avg": int(ui.num(r["avg_daily"])), "wd": int(ui.num(r["avg_weekday"])),
                 "we": int(ui.num(r["avg_weekend"])), "ratio": ui.num(r["weekday_weekend_ratio"]), "dry": int(ui.num(r["avg_dry"])),
                 "rainy": int(ui.num(r["avg_rainy"])), "pen": ui.num(r["rain_penalty"]), "deg": ui.num(r["cyclists_per_degree"]),
                 "sun": ui.num(r["corr_sunshine"]), "rec": ui.num(r["recovery_ratio"]), "rrank": int(ui.num(r["recovery_rank"]))} for r in c]

        d = ui.lower(q("queries/daily.sql"))
        daily = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.06)
        if d and not d[0].get("_error"):
            for st in colors:
                sub = [r for r in d if r["station"] == st]
                daily.add_trace(go.Scatter(x=[r["count_date"] for r in sub], y=[ui.num(r["total"]) for r in sub], mode="lines", name=names[st],
                                           line={"color": colors[st], "width": 1.6}, hovertemplate=names[st] + ": %{y:,.0f}<extra></extra>"), row=1, col=1)
            first = c[0]["station"]
            wx = [r for r in d if r["station"] == first]
            daily.add_trace(go.Bar(x=[r["count_date"] for r in wx], y=[ui.num(r["rain_mm"]) for r in wx], name="Rain, mm", marker={"color": RAINY},
                                   hovertemplate="rain %{y:.1f} mm<extra></extra>"), row=2, col=1)
        ui.theme(daily, hovermode="x unified", yaxis={"title": "Cyclists per day"}, yaxis2={"title": "Rain, mm", "gridcolor": ui.GRID},
                 xaxis2={"gridcolor": ui.GRID}, bargap=0.1)

        rb = go.Figure()
        rb.add_bar(x=[r["station_name"] for r in c], y=[ui.num(r["avg_dry"]) for r in c], name="Dry days", marker={"color": DRY})
        rb.add_bar(x=[r["station_name"] for r in c], y=[ui.num(r["avg_rainy"]) for r in c], name="Rainy days", marker={"color": RAINY})
        ui.theme(rb, barmode="group", yaxis={"title": "Average daily cyclists"}, xaxis={"tickangle": -20, "automargin": True, "tickfont": {"size": 10}})

        wb = go.Figure()
        wb.add_bar(x=[r["station_name"] for r in c], y=[ui.num(r["avg_weekday"]) for r in c], name="Weekday", marker={"color": WEEKDAY})
        wb.add_bar(x=[r["station_name"] for r in c], y=[ui.num(r["avg_weekend"]) for r in c], name="Weekend", marker={"color": WEEKEND})
        ui.theme(wb, barmode="group", yaxis={"title": "Average daily cyclists"}, xaxis={"tickangle": -20, "automargin": True, "tickfont": {"size": 10}})

        wbands = ui.lower(q("queries/weather_bands.sql"))
        tl = go.Figure()
        if wbands and not wbands[0].get("_error"):
            for st in colors:
                sub = sorted([r for r in wbands if r["station"] == st and r["wx"] == "dry"], key=lambda r: ui.num(r["temp_band_from"]))
                tl.add_scatter(x=[f"{int(ui.num(r['temp_band_from']))}–{int(ui.num(r['temp_band_from'])) + 5} °C" for r in sub], y=[ui.num(r["avg_daily"]) for r in sub],
                               mode="lines+markers", name=names[st], line={"color": colors[st], "width": 2}, marker={"size": 8},
                               customdata=[int(ui.num(r["days"])) for r in sub], hovertemplate=names[st] + ": %{y:,.0f} (%{customdata} dry days)<extra></extra>")
        ui.theme(tl, hovermode="x unified", yaxis={"title": "Average daily cyclists"}, xaxis={"title": "Maximum temperature"})

        s = ui.lower(q("queries/stations.sql"))
        mp = go.Figure()
        if s and not s[0].get("_error"):
            mp.add_trace(go.Scattermap(lat=[ui.num(r["lat"]) for r in s], lon=[ui.num(r["lon"]) for r in s], mode="markers+text", text=[r["station_name"] for r in s],
                                       textposition="top right", textfont={"size": 11, "color": ui.INK},
                                       marker={"size": [10 + ui.num(r["avg_daily"]) / 200 for r in s], "color": [colors.get(r["station"], ui.MUTED) for r in s], "opacity": 0.9},
                                       hovertext=[f"<b>{r['station_name']}</b><br>{r['district_name']}<br>{ui.fmt(r['avg_daily'])} cyclists per day" for r in s], hoverinfo="text"))
        ui.map_layout(mp, {"lat": 48.142, "lon": 11.565}, 11.3)
        mp.update_layout(showlegend=False)

        m = ui.lower(q("queries/monthly.sql"))
        ml = go.Figure()
        if m and not m[0].get("_error"):
            for st in colors:
                sub = [r for r in m if r["station"] == st]
                ml.add_scatter(x=[r["month_key"] for r in sub], y=[ui.num(r["avg_daily"]) for r in sub], mode="lines+markers", name=names[st],
                               line={"color": colors[st], "width": 2}, marker={"size": 8}, customdata=[[ui.num(r["avg_temp_max"]), ui.num(r["rain_mm"])] for r in sub],
                               hovertemplate=names[st] + ": %{y:,.0f} per day · avg max %{customdata[0]:.1f} °C · %{customdata[1]:.0f} mm rain<extra></extra>")
        ui.theme(ml, hovermode="x unified", yaxis={"title": "Average daily cyclists"}, xaxis={"type": "category"})

        h = ui.lower(q("queries/heatmap.sql"))
        heat = [] if (not h or h[0].get("_error")) else [{"s": r["station"], "d": int(ui.num(r["iso_weekday"])), "h": int(ui.num(r["hour_of_day"])), "v": ui.num(r["avg_cyclists_per_hour"])} for r in h]
        return kpis, meta, daily, rb, tl, wb, rows, None, mp, ml, heat, [{"label": names[st], "value": st} for st in colors], c[0]["station"]

    @app.callback(Output("heatmap", "figure"), Input("heat-store", "data"), Input("heat-counter", "value"))
    def heatmap(heat, station):
        fig = go.Figure()
        sub = [r for r in (heat or []) if r["s"] == station]
        if sub:
            z = [[0.0] * 24 for _ in range(7)]
            for r in sub:
                if 1 <= r["d"] <= 7 and 0 <= r["h"] <= 23:
                    z[r["d"] - 1][r["h"]] = r["v"]
            fig.add_trace(go.Heatmap(z=z, x=[f"{h:02d}" for h in range(24)], y=WEEKDAYS, colorscale=ui.ramp_scale(ui.RAMP_GREEN), xgap=2, ygap=2,
                                     hovertemplate="%{y} %{x}:00 · %{z:.0f} cyclists per hour<extra></extra>", colorbar={"thickness": 10, "title": {"text": "per hour"}}))
        return ui.theme(fig, xaxis={"title": "Hour of day", "gridcolor": ui.SURFACE}, yaxis={"autorange": "reversed", "gridcolor": ui.SURFACE})

    return app
