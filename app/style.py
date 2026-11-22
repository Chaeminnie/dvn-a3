"""Shared styles for the app.

Please import colours, chart settings and layout blocks from here instead of hard-coding them, e.g.
    style.section(...), style.kpi_row(...), style.plotly_chart(style.plotly_theme(fig, ...))
"""
from __future__ import annotations

import html

import altair as alt
import plotly.graph_objects as go
import streamlit as st

# Tokens
# Neutrals: white page, soft grey fills, no hard borders.
INK = "#191f28"  # titles, numbers
TEXT = "#333d4b"  # body
SUB = "#4e5968"  # takeaways, secondary text
MUTED = "#8b95a1"  # captions, axis labels
LINE = "#e5e8eb"  # hairlines
FILL = "#f2f4f6"  # cards, inputs
FILL_SOFT = "#f9fafb"  # sidebar, expanders
SURFACE = "#ffffff"

# Highlight colours (blue/orange is colour-blind safe)
SELECTED = "#3182f6"  # the tokenizer you picked
FOCUS = "#ff6f0f"  # the focus language
CONTEXT = "#c4cad1"  # everything else
ACCENT_BG = "#e8f3ff"  # answer box
ACCENT_INK = "#1b64da"

# Tokenizer families
FAMILY = {"gpt": "#3182f6", "gemma": "#ff6f0f", "qwen": "#1baf7a", "claude": "#eda100",
          "llama": "#e87ba4", "mistral": "#008300", "gemini": "#6250d6"}
# Heatmap steps, light to dark
SEQ = ["#f4f8fe", "#dbeafe", "#b9d6fc", "#88b9f9", "#4f95f5", "#2570e0", "#174aa0"]

FONT = "Pretendard Variable, Pretendard, -apple-system, 'Segoe UI', system-ui, sans-serif"
FONT_URL = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
RADIUS = 16  # cards
RADIUS_SM = 10  # inputs, nav items
CHART_HEIGHT = 420
PLOT_CONFIG = {"displayModeBar": False}


# Format
def fmt_x(v: float, digits: int = 1) -> str:
    """1.4321 -> '1.4×'"""
    return f"{v:.{digits}f}×"


def fmt_pct(v: float, digits: int = 0) -> str:
    return f"{v * 100:.{digits}f}%"


def colours_for(names, focus=None, selected=None):
    """Focus name orange, selected name blue, the rest grey."""
    return [FOCUS if n == focus else SELECTED if n == selected else CONTEXT for n in names]


# Charts
def plotly_theme(fig: go.Figure, *, x_title: str | None, y_title: str | None, height: int = CHART_HEIGHT) -> go.Figure:
    """Apply the shared Plotly look. Axis titles are keyword-only so they don't get skipped."""
    fig.update_layout(
        height=height,
        margin=dict(l=4, r=24, t=28, b=4),
        font=dict(family=FONT, size=13, color=TEXT),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        hoverlabel=dict(font=dict(family=FONT, size=13, color=INK), bgcolor=SURFACE, bordercolor=LINE),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=12, color=SUB), title_text=""),
        bargap=0.35,
    )
    fig.update_xaxes(title_text=x_title, title_font=dict(color=MUTED, size=12), tickfont=dict(color=MUTED, size=12),
                     gridcolor=FILL, linecolor=LINE, zeroline=False, automargin=True)
    fig.update_yaxes(title_text=y_title, title_font=dict(color=MUTED, size=12), tickfont=dict(color=TEXT, size=13),
                     gridcolor=FILL, linecolor=LINE, zeroline=False, automargin=True)
    fig.update_traces(selector=dict(type="bar"), marker_cornerradius=6)
    return fig


@alt.theme.register("dvn", enable=True)
def _altair_theme() -> alt.theme.ThemeConfig:
    return {
        "config": {
            "background": SURFACE,
            "font": FONT,
            "view": {"stroke": None},
            "axis": {"labelColor": MUTED, "titleColor": MUTED, "titleFontWeight": "normal", "titleFontSize": 12,
                     "labelFontSize": 12, "gridColor": FILL, "domainColor": LINE, "tickColor": LINE, "labelPadding": 6},
            "axisY": {"labelColor": TEXT, "labelFontSize": 13},
            "legend": {"orient": "top", "labelColor": SUB, "titleColor": MUTED, "labelFontSize": 12, "symbolType": "circle"},
            "text": {"color": INK, "fontSize": 12, "font": FONT},
            "bar": {"cornerRadiusEnd": 6},
            "range": {"category": list(FAMILY.values())},
        }
    }


def plotly_chart(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG, theme=None)


def altair_chart(chart) -> None:
    st.altair_chart(chart, width="stretch", theme=None)


# Blocks
def _html(s: str) -> None:
    st.markdown(s, unsafe_allow_html=True)


def section(title: str, takeaway: str) -> None:
    """Tab title plus a one-line takeaway."""
    _html(f"<div class='dvn-section'><h2>{html.escape(title)}</h2><p>{takeaway}</p></div>")


def chart_title(title: str, caption: str) -> None:
    """Chart title with a short caption underneath."""
    _html(f"<div class='dvn-chart-title'><b>{html.escape(title)}</b><span>{caption}</span></div>")


def kpi_row(items: list[tuple]) -> None:
    """items = [(label, value, help_text), ...]. Three at most."""
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        label, value, *rest = item
        col.metric(label, value, help=rest[0] if rest else None)


def answer(text: str) -> None:
    _html(f"<div class='dvn-answer'>{text}</div>")


def callout(title: str, body: str = "") -> None:
    """Grey note box, e.g. the link from tab 2 to tab 3."""
    _html(f"<div class='dvn-callout'><b>{title}</b><span>{body}</span></div>")


def table(df, **column_config) -> None:
    st.dataframe(df, hide_index=True, width="stretch", column_config=column_config or None)


def how_to_read(text: str) -> None:
    with st.expander("How to read this", icon=":material/menu_book:"):
        st.markdown(text)


def not_shown(*points: str) -> None:
    with st.expander("What this does not show", icon=":material/visibility_off:"):
        st.markdown("\n".join(f"- {p}" for p in points))


def empty_state(message: str = "Nothing to show. Pick at least one script group in the sidebar.") -> None:
    _html(f"<div class='dvn-empty'>{message}</div>")


def placeholder(what: str, owner: str, height: int = 320) -> None:
    """Grey box standing in for a chart that isn't built yet."""
    _html(f"<div class='dvn-ph' style='height:{height}px'><b>{html.escape(what)}</b><span>Owner: {owner}</span></div>")


# CSS
def inject_css() -> None:
    _html(f"""<style>
@import url('{FONT_URL}');
.stApp, .stApp *, button, input, textarea, select {{font-family: {FONT} !important;}}
.stApp [data-testid="stIconMaterial"], .stApp span[translate="no"], .stApp [data-testid$="Icon"] {{font-family: "Material Symbols Rounded" !important;}}
.block-container {{padding-top: 2.4rem; padding-bottom: 4rem; max-width: 1160px;}}
header[data-testid="stHeader"] {{background: transparent;}}
p, li {{color: {TEXT};}}

/* sidebar + nav */
[data-testid="stSidebar"] {{background: {FILL_SOFT}; border-right: 1px solid {LINE};}}
[data-testid="stSidebarNavLink"] {{border-radius: {RADIUS_SM}px; padding: 6px 10px; margin: 1px 0;}}
[data-testid="stSidebarNavLink"] span {{color: {SUB}; font-weight: 500;}}
[data-testid="stSidebarNavLink"]:hover {{background: {FILL};}}
[data-testid="stSidebarNavLink"][aria-current="page"] {{background: {ACCENT_BG};}}
[data-testid="stSidebarNavLink"][aria-current="page"] span {{color: {ACCENT_INK}; font-weight: 700;}}
[data-testid="stSidebarNavSeparator"] {{display: none;}}
.dvn-brand {{font-size: 19px; font-weight: 800; color: {INK}; line-height: 1.25; letter-spacing: -0.02em; margin: 0 0 .2rem;}}
.dvn-label {{font-size: 12px; font-weight: 600; color: {MUTED}; margin: .6rem 0 .2rem;}}

/* app title: page header on Overview, sidebar header on every tab */
.dvn-title {{font-size: 34px; font-weight: 800; color: {INK}; letter-spacing: -0.03em; line-height: 1.2; margin: 0 0 .8rem;}}
[data-testid="stSidebarNav"]::before {{content: "Same sentence, different bill"; display: block; font-size: 19px;
  font-weight: 800; color: {INK}; line-height: 1.25; letter-spacing: -0.02em; padding: 4px 10px 14px;}}

/* header */
.dvn-q {{font-size: 15px; color: {SUB}; line-height: 1.55; margin: 0 0 .7rem;}}
.dvn-q b {{color: {INK};}}
.dvn-answer {{background: {ACCENT_BG}; color: {ACCENT_INK}; border-radius: {RADIUS}px; padding: 16px 20px;
  font-size: 15px; line-height: 1.55; margin-bottom: .6rem;}}
.dvn-answer b {{font-weight: 700;}}

/* section */
.dvn-section h2 {{font-size: 26px; font-weight: 800; color: {INK}; letter-spacing: -0.02em; margin: 1.6rem 0 .25rem; padding: 0;}}
.dvn-section p {{font-size: 16px; color: {SUB}; margin: 0 0 .6rem;}}
.dvn-chart-title {{margin: 1.2rem 0 .3rem;}}
.dvn-chart-title b {{display: block; font-size: 17px; font-weight: 700; color: {INK}; letter-spacing: -0.01em;}}
.dvn-chart-title span {{display: block; font-size: 14px; color: {MUTED}; margin-top: 2px;}}

/* KPI cards */
[data-testid="stMetric"] {{background: {FILL}; border-radius: {RADIUS}px; padding: 18px 20px;}}
[data-testid="stMetricLabel"] p {{color: {SUB}; font-size: 14px; font-weight: 500;}}
[data-testid="stMetricValue"] {{color: {INK}; font-size: 30px; font-weight: 800; letter-spacing: -0.02em;}}

/* boxes */
[data-testid="stExpander"] details {{border: none; background: {FILL_SOFT}; border-radius: {RADIUS_SM + 2}px;}}
[data-testid="stExpander"] summary p {{font-weight: 600; color: {TEXT};}}
.dvn-callout {{background: {FILL}; border-radius: {RADIUS}px; padding: 16px 20px; margin: .8rem 0;}}
.dvn-callout b {{display: block; color: {INK}; font-size: 16px;}}
.dvn-callout span {{color: {SUB}; font-size: 14px;}}
.dvn-empty {{background: {FILL_SOFT}; border: 1px dashed {LINE}; border-radius: {RADIUS}px; padding: 28px; text-align: center; color: {MUTED};}}
.dvn-ph {{background: {FILL}; border-radius: {RADIUS}px; display: flex; flex-direction: column; align-items: center;
  justify-content: center; text-align: center; padding: 0 32px; margin: .2rem 0 .8rem;}}
.dvn-ph b {{color: {SUB}; font-size: 14px; font-weight: 600;}}
.dvn-ph span {{color: {MUTED}; font-size: 12px; margin-top: 4px;}}

/* inputs and pills */
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="base-input"] {{border-radius: {RADIUS_SM}px !important;}}
[data-testid="stBaseButton-pills"], [data-testid="stBaseButton-pillsActive"] {{border-radius: 999px; font-weight: 500;}}
[data-testid="stBaseButton-pillsActive"] {{background: {ACCENT_BG} !important; color: {ACCENT_INK} !important; border-color: transparent !important;}}
[data-testid="stCaptionContainer"] {{color: {MUTED};}}
hr {{border-color: {LINE};}}
</style>""")
