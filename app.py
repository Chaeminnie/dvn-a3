"""Do some languages cost more tokens than others? DVN Assignment 3 prototype.

Run:  streamlit run app.py
The app only reads the committed CSV files in data/, so DASHBOARD_SAMPLE_MODE
(declared in dashboard.yml) has no extra effect: the committed files are the sample.
"""

from __future__ import annotations

import streamlit as st

from src import views

st.set_page_config(page_title="AI language token cost", layout="wide")
# Pull the title up so the question and headline numbers sit on the first screen at 1366x768.
st.markdown("<style>.block-container{padding-top:2.5rem;}</style>", unsafe_allow_html=True)

views.render_opening()
views.render_trend_view()
views.render_premium_view()
views.render_pricing_banner()
views.render_buffer_view()
views.render_tier_view()
views.render_footer()
