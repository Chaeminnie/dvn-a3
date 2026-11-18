"""Tab 1: Script or tokenizer? Owner: Chandan.

TODO (Chandan): bring charts A and B from the `chandan` branch into render().
Use state.tokenizer, state.focus and state.languages (the sidebar filters) instead of your own widgets.
When state.languages is empty, call style.empty_state() instead of drawing a chart.
"""
import streamlit as st

import style


def render(state):
    style.section("Is it the script or the tokenizer?", "TODO: one sentence with the finding.")
    if not state.languages:
        return style.empty_state()
    style.kpi_row([("Script alone (focus language)", "-", None), ("On the selected tokenizer", "-", None),
                   ("Tokenizer swing", "-", None)])
    a, b = st.columns(2, gap="large")
    with a:
        style.chart_title("Who pays the most?", "TODO: caption")
        style.placeholder("Bar · tokens vs English per language · labels at bar ends", "Chandan", 420)
    with b:
        style.chart_title("Is it the script?", "TODO: caption")
        style.placeholder("Scatter · bytes vs tokens · dashed 'script only' line · labelled dots", "Chandan", 420)
    style.how_to_read("TODO")
    style.not_shown("TODO")
