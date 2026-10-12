"""Shared look for the four Munich dashboards: tokens, header, stat tiles, cards, chart theme, tables.

Copied unchanged into every app workspace next to app.py. Colours follow a validated
categorical order (CVD-safe adjacent pairs); never cycle a new hue, never a dual axis.
"""
from dash import dash_table, dcc, html
import plotly.graph_objects as go

FONT = "Inter, -apple-system, 'Segoe UI', Roboto, sans-serif"
STYLESHEETS = ["https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"]

# surfaces and ink
PAGE, SURFACE, LINE, GRID = "#f4f4f1", "#ffffff", "#e7e6e1", "#eeede9"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"

# categorical slots in the validated order (light mode)
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
# one persona, one accent
PERSONA = {"ops": "#eb6834", "planning": "#2a78d6", "sustainability": "#1baf7a", "leadership": "#4a3aa7"}
# transit modes in stack order; night lines (<1 % of departures) are folded out of the charts
MODES = {"Bus": SLOTS[0], "Tram": SLOTS[1], "U-Bahn": SLOTS[2], "S-Bahn": SLOTS[3], "Regional rail": SLOTS[4]}
# sequential ramps, one hue each
RAMP_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
RAMP_ORANGE = ["#fde4d8", "#f9bda3", "#f4956f", "#eb6834", "#c8502a", "#9f3d1f", "#742b15"]
RAMP_GREEN = ["#d7f3e6", "#a6e4c8", "#6fd1a8", "#1baf7a", "#15915f", "#0f6f49", "#0a4e33"]
RAMP_VIOLET = ["#e7e4f6", "#c8c1ea", "#a69bdc", "#7f71ce", "#5e4fb6", "#4a3aa7", "#342775"]
TEXTURE = "/"  # plotly marker pattern for the print / forced-colours case


def ramp_scale(ramp):
    n = len(ramp) - 1
    return [[i / n, c] for i, c in enumerate(ramp)]


def lower(rows):
    """Exasol returns upper-case keys; the apps address columns in lower case."""
    return [{str(k).lower(): v for k, v in r.items()} for r in rows]


def num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def fmt(v, nd=0):
    return f"{num(v):,.{nd}f}"


CARD = {"background": SURFACE, "border": f"1px solid {LINE}", "borderRadius": "12px", "padding": "16px 18px",
        "boxShadow": "0 1px 2px rgba(11,11,11,.04)"}


def page(children, *, eyebrow, title, subtitle, accent, meta=None):
    """Page shell: coloured eyebrow + title band, then the children."""
    header = html.Div([
        html.Div([
            html.Div(eyebrow, style={"fontSize": "12px", "fontWeight": 600, "letterSpacing": ".08em", "textTransform": "uppercase", "color": accent}),
            html.H1(title, style={"margin": "4px 0 6px", "fontSize": "28px", "fontWeight": 700, "letterSpacing": "-.01em", "color": INK}),
            html.Div(subtitle, style={"fontSize": "14px", "color": INK2, "maxWidth": "820px", "lineHeight": 1.5}),
            html.Div(meta or "", id="page-meta", style={"fontSize": "12px", "color": MUTED, "marginTop": "8px"}),
        ], style={"borderLeft": f"4px solid {accent}", "paddingLeft": "16px"}),
    ], style={"padding": "4px 0 18px"})
    return html.Div([header, *children],
                    style={"fontFamily": FONT, "background": PAGE, "padding": "22px 28px 40px", "minHeight": "100vh", "color": INK,
                           "maxWidth": "1480px", "margin": "0 auto"})


def tile(label, value, note=None, accent=None):
    return html.Div([
        html.Div(label, style={"fontSize": "12px", "fontWeight": 500, "color": INK2, "letterSpacing": ".02em"}),
        html.Div(value, style={"fontSize": "30px", "fontWeight": 700, "color": INK, "marginTop": "6px", "letterSpacing": "-.02em",
                               "fontVariantNumeric": "tabular-nums", "lineHeight": 1.1}),
        html.Div(note or " ", style={"fontSize": "12px", "color": MUTED, "marginTop": "6px"}),
    ], style={**CARD, "flex": "1 1 190px", "minWidth": "180px", "borderTop": f"3px solid {accent or LINE}"})


def tiles(children):
    return html.Div(children, style={"display": "flex", "gap": "12px", "flexWrap": "wrap"})


def card(title, body, subtitle=None, flex="1 1 480px", min_width="320px"):
    kids = [html.H3(title, style={"margin": "0 0 2px", "fontSize": "15px", "fontWeight": 600, "color": INK})]
    if subtitle:
        kids.append(html.Div(subtitle, style={"fontSize": "12px", "color": MUTED, "marginBottom": "8px", "lineHeight": 1.45}))
    kids.append(html.Div(body, style={"marginTop": "6px"}))
    return html.Div(kids, style={**CARD, "flex": flex, "minWidth": min_width})


def row(children):
    return html.Div(children, style={"display": "flex", "gap": "12px", "flexWrap": "wrap", "marginTop": "12px"})


def block(child):
    return html.Div(child, style={"marginTop": "12px"})


def notes(title, items):
    return html.Details([
        html.Summary(title, style={"cursor": "pointer", "fontWeight": 600, "fontSize": "14px"}),
        html.Ul([html.Li(i) for i in items], style={"color": INK2, "fontSize": "13px", "lineHeight": 1.55, "margin": "8px 0 0"}),
    ], style={**CARD, "marginTop": "12px"})


def graph(id_, height=380, **kw):
    cfg = {"displayModeBar": False, "responsive": True}
    cfg.update(kw.pop("config", {}))
    return dcc.Loading(dcc.Graph(id=id_, config=cfg, style={"height": f"{height}px", "width": "100%"}), type="dot", color=MUTED)


def theme(fig, **kw):
    """Recessive axes and grid, legend on top, consistent hover card, thin rounded bars."""
    layout = {
        "paper_bgcolor": SURFACE, "plot_bgcolor": SURFACE,
        "font": {"family": FONT, "size": 12, "color": INK2},
        "margin": {"l": 8, "r": 8, "t": 8, "b": 36},
        "hoverlabel": {"bgcolor": INK, "bordercolor": INK, "font": {"family": FONT, "size": 12, "color": "#ffffff"}},
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0, "font": {"size": 12}, "itemwidth": 30},
        "xaxis": {"gridcolor": GRID, "zerolinecolor": LINE, "linecolor": LINE, "tickfont": {"size": 11}, "title": {"font": {"size": 12, "color": MUTED}}},
        "yaxis": {"gridcolor": GRID, "zerolinecolor": LINE, "linecolor": LINE, "tickfont": {"size": 11}, "title": {"font": {"size": 12, "color": MUTED}}},
        "bargap": 0.28, "bargroupgap": 0.08, "barcornerradius": 4,
    }
    for k, v in kw.items():
        if isinstance(v, dict) and isinstance(layout.get(k), dict):
            layout[k] = {**layout[k], **v}
        else:
            layout[k] = v
    fig.update_layout(**layout)
    return fig


def empty(msg):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font={"color": MUTED, "size": 13})
    return theme(fig, xaxis={"visible": False}, yaxis={"visible": False})


def map_layout(fig, center, zoom):
    fig.update_layout(map={"style": "carto-positron", "center": center, "zoom": zoom},
                      margin={"l": 0, "r": 0, "t": 0, "b": 0}, paper_bgcolor=SURFACE, font={"family": FONT, "size": 12},
                      hoverlabel={"bgcolor": INK, "bordercolor": INK, "font": {"family": FONT, "size": 12, "color": "#ffffff"}},
                      legend={"x": 0.01, "y": 0.99, "bgcolor": "rgba(255,255,255,.92)", "bordercolor": LINE, "borderwidth": 1, "font": {"size": 12}})
    return fig


def table(id_, columns, numeric_ids=(), highlight=None, page_size=25, accent=None):
    """DataTable with the shared type: left text, right numbers, zebra-free, accent on the key column."""
    cond = [{"if": {"column_id": list(numeric_ids)}, "textAlign": "right"}]
    if highlight:
        cond.append({"if": {"column_id": highlight}, "fontWeight": 700, "color": accent or INK})
    return dash_table.DataTable(
        id=id_, columns=columns, page_size=page_size, sort_action="native",
        style_table={"overflowX": "auto"},
        style_cell={"fontFamily": FONT, "fontSize": "13px", "padding": "7px 10px", "textAlign": "left", "whiteSpace": "normal",
                    "height": "auto", "maxWidth": "280px", "border": "none", "borderBottom": f"1px solid {GRID}", "color": INK},
        style_header={"fontWeight": 600, "fontSize": "12px", "color": INK2, "backgroundColor": SURFACE, "borderBottom": f"2px solid {LINE}",
                      "textTransform": "uppercase", "letterSpacing": ".03em"},
        style_data_conditional=cond,
        css=[{"selector": ".dash-table-container .previous-next-container", "rule": f"font-family: {FONT}; color: {INK2};"}],
    )


def error_panel(message):
    return html.Div([html.Strong("Exasol query failed"), html.Pre(message or "Unknown Exasol error", style={"whiteSpace": "pre-wrap"})],
                    style={"backgroundColor": "#fff4ec", "border": "1px solid #f4b48e", "borderRadius": "10px", "padding": "12px 14px", "fontSize": "13px"})
