"""Template for a tab. Copy it to sections/<your_tab>.py.

Rules:
- Only render(state). No st.set_page_config, no st.sidebar, no CSS.
- Read the shared choices from state (tokenizer, focus, languages). Don't add your own copies.
- Colours, labels and numbers: import from style and data only.
- Widget defaults: st.session_state.setdefault("my_key", 10), then st.number_input(..., key="my_key") without value=.
- Every value readable without hovering: put labels on bars and dots.
"""
import plotly.graph_objects as go

import style
from data import TOKENIZER


def render(state):
    style.section("Your question as a title", "One sentence that states what the chart shows.", owner="Your name")
    p = state.d["prem"]
    d = p[(p.tokenizer_id == state.tokenizer) & p.language.isin(state.languages)]
    if d.empty:
        return style.empty_state()

    style.kpi_row([("Label with unit", style.fmt_x(2.0), "What it means")])

    style.chart_title("Chart title", f"What the chart shows, on {TOKENIZER[state.tokenizer]}.")
    fig = go.Figure()  # your chart
    style.plotly_chart(style.plotly_theme(fig, x_title="X with unit (×)", y_title=None))

    style.how_to_read("How to read it.")
    style.not_shown("What the data cannot tell you.")
