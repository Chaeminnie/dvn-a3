"""Same sentence, different bill. DVN A3 group app.

Run from the repo root: streamlit run app/app.py
Each tab is in app/sections/<name>.py and exposes render(state).
"""
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

import data
import style
from sections import costs, overview, script, shrinking, verify

st.set_page_config(page_title="Same sentence, different bill", page_icon=":material/translate:", layout="wide")
style.inject_css()
D = data.load()


@dataclass
class State:
    """Selections from the sidebar, passed to every tab."""
    tokenizer: str  # tokenizer_id, e.g. "o200k_base"
    focus: str  # language name, e.g. "Burmese"
    languages: list  # language names allowed by the script filter
    d: dict  # everything from data.load()


ss = st.session_state
# Defaults go in session_state (not value=/index=) so they survive tab switches
ss.setdefault("tokenizer", "o200k_base")
ss.setdefault("focus", "Burmese")
ss.setdefault("scripts", list(data.SCRIPT_GROUPS))
# Streamlit drops widget values for pages that aren't shown, so write them back
for _k in list(ss.keys()):
    try:
        ss[_k] = ss[_k]
    except Exception:
        pass

# Sidebar filters
with st.sidebar:
    st.markdown("<div class='dvn-label'>Filters</div>", unsafe_allow_html=True)
    tok_ids = list(data.TOKENIZER)
    tokenizer = st.selectbox("Tokenizer", tok_ids, format_func=data.TOKENIZER.get, key="tokenizer")
    others = sorted(l for l in D["langs"]["language"] if l != "English")
    focus = st.selectbox("Focus language", others, key="focus")
    groups = st.pills("Script groups", list(data.SCRIPT_GROUPS), selection_mode="multi", key="scripts")
    codes = [c for g in (groups or []) for c in data.SCRIPT_GROUPS[g]]
    allowed = D["langs"].loc[D["langs"]["iso_15924"].isin(codes), "language"].tolist()
    st.divider()
    st.caption(f"Data refreshed **{D['refreshed']}**")

state = State(tokenizer=tokenizer, focus=focus, languages=allowed, d=D)


def _page(module, title, icon, path):
    def run():
        module.render(state)
    run.__name__ = path
    return st.Page(run, title=title, icon=icon, url_path=path, default=(path == "overview"))


nav = st.navigation([
    _page(overview, "Overview", ":material/grid_view:", "overview"),
    _page(script, "Script or tokenizer?", ":material/translate:", "script"),
    _page(shrinking, "Is it shrinking?", ":material/trending_down:", "shrinking"),
    _page(costs, "Absorb, adjust or switch?", ":material/payments:", "costs"),
], position="sidebar")


def _study_block():
    st.markdown(f"<p class='dvn-q'><b>Question.</b> {data.QUESTION}<br><b>For.</b> {data.PERSONA}.</p>",
                unsafe_allow_html=True)
    style.answer("<b>Answer: mostly the tokenizer.</b> The same text costs very different amounts on different "
                 "tokenizers. Newer tokenizers narrow the gap, but it has not closed.")


# Header: open with the app title on Overview, collapsed on the other tabs
if nav.title == "Overview":
    st.markdown("<div class='dvn-title'>Same sentence, different bill</div>", unsafe_allow_html=True)
    _study_block()
else:
    with st.expander("The study question and answer", icon=":material/help:"):
        _study_block()

# Tab body
nav.run()

# Footer (every tab)
st.divider()
st.caption(f"Sources: FLORES+ devtest, 200-sentence sample (sampling error up to about 3%); tokenizer libraries; "
           f"list prices. Files in data/source and data/processed. Data refreshed {D['refreshed']}.")
f1, f2, f3 = st.columns(3)
with f1:
    with st.expander("Check a number", icon=":material/fact_check:"):
        verify.render(state)
with f2:
    with st.expander("Limitations", icon=":material/info:"):
        verify.limitations()
with f3:
    with st.expander("Data and AI disclosure", icon=":material/policy:"):
        st.markdown("AI use is listed per person, with the check each of us ran, in the "
                    "[AI provenance matrix](https://github.com/Chaeminnie/dvn-a3/blob/main/AI_PROVENANCE.md). "
                    "The disclosure statement is at the bottom of the same file.")
