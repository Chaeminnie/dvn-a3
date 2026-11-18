"""Tab 3: Absorb, adjust or switch? Owner: Amanda.

TODO (Amanda): bring the calculator from the `Chaemin` branch (language mix editor, upload, service inputs,
results) and the tier chart from your `amanda` branch. Saloni's budget framing ("$X gets you Y% of English")
from `calculator-saloni` can be one line in the results.
Widget defaults: st.session_state.setdefault("key", value), then the widget with key= and no value=.
"""
import streamlit as st

import style


def render(state):
    style.section("Absorb, adjust or switch?", "TODO: one sentence, e.g. 'Compare three options on your own language mix.'")
    left, right = st.columns([1, 2], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("**Your inputs**")
            style.placeholder("Language mix · users · requests · tokens · English-only share · price", "Amanda", 360)
    with right:
        style.kpi_row([("Blended premium", "-", None), ("Monthly bill", "-", None), ("Extra vs English", "-", None)])
        o1, o2, o3 = st.columns(3)
        for col, name in zip((o1, o2, o3), ("Absorb", "Adjust plans and quotas", "Switch model")):
            col.metric(name, "-")
    style.chart_title("What one price vs three tiers overcharges", "TODO: caption with the tier cut-offs.")
    style.placeholder("Dot plot · overcharge per language · one price vs tiers · labels on dots", "Amanda", 320)
    style.how_to_read("TODO")
    style.not_shown("TODO")
