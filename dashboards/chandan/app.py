import streamlit as st

import charts
from loaders import IDENTICAL, NAMES, family_change, headline, load

QUESTION = ("Is the extra token cost of non-English languages a fixed property of their "
            "scripts, or a result of tokenizer design choices that is shrinking?")

# Script groups for the filter, keyed by ISO 15924 code from lang_meta.csv.
SCRIPT_GROUPS = {
    "Latin": ["Latn"],
    "Other alphabets": ["Cyrl", "Arab", "Hang", "Ethi"],
    "South & Southeast Asian": ["Deva", "Taml", "Thai", "Mymr"],
    "Chinese & Japanese": ["Hans", "Jpan"],
}

st.set_page_config(page_title="Script or tokenizer?", page_icon=":material/translate:",
                   layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>.block-container{padding-top:2rem;max-width:1360px}</style>",
            unsafe_allow_html=True)


def theme_colours():
    # st.context.theme only exists in newer Streamlit versions, so fall back to light.
    try:
        return charts.DARK if st.context.theme.type == "dark" else charts.LIGHT
    except Exception:
        return charts.LIGHT


c = theme_colours()
prem, gini, langs, refreshed = load()
h = headline(prem, gini)
fam = {r["family"]: r for r in family_change(gini)}
cfg = {"displayModeBar": False}

# ---------- Header ----------

st.title("Is it the script, or the tokenizer?")
st.caption(f"**Question:** {QUESTION}  \n**For:** an AI pricing lead deciding whether to absorb, "
           "charge for, or fix the extra token cost of non-English users.")

# Facts about the whole dataset. Filters below don't change these.
w, s, lo, hi = h["worst"], h["script_max"], h["swing_lo"], h["swing_hi"]
k1, k2, k3, k4 = st.columns(4)
k1.metric(f"Worst case ({w['language']}, {w['tokenizer']})", f"{w['premium_vs_en']:.1f}×",
          help="Tokens needed for the same text, compared with English.", border=True)
k2.metric(f"Script alone ({s['language']})", f"{s['byte_premium_vs_en']:.1f}×",
          help="How much bigger the text is than English in UTF-8 bytes. Same on every tokenizer.",
          border=True)
k3.metric(f"Tokenizer swing ({h['swing_lang']})", f"{h['swing_ratio']:.1f}×",
          help=f"{lo['premium_vs_en']:.1f}× on {lo['tokenizer']}, "
               f"{hi['premium_vs_en']:.1f}× on {hi['tokenizer']}.", border=True)
k4.metric("Pairs costing more than their script", f"{h['share_above']:.0%}",
          help=f"Share of {h['n_pairs']} language and tokenizer pairs, English left out.",
          border=True)

g = fam["gemma"]
q = fam["qwen"]
st.info(
    f"**Answer: mostly the tokenizer.** {h['swing_lang']} text is always "
    f"{lo['byte_premium_vs_en']:.1f}× English in bytes, but costs anywhere from "
    f"{lo['premium_vs_en']:.1f}× to {hi['premium_vs_en']:.1f}× depending on the tokenizer. "
    f"Newer tokenizers can close the gap (Gemma 2 → 3: Gini {g['first']['gini']:.2f} → "
    f"{g['last']['gini']:.2f}), but not all do (Qwen 2.5 → 3: {q['first']['gini']:.2f} → "
    f"{q['last']['gini']:.2f}).",
    icon=":material/lightbulb:",
)

# ---------- Filters ----------

tok_ids = list(NAMES)
focus_options = sorted(l for l in langs["language"] if l != "English")

f1, f2, f3 = st.columns([1, 1, 2])
tok_id = f1.selectbox("Tokenizer", tok_ids, index=tok_ids.index("o200k_base"),
                      format_func=NAMES.get)
focus = f2.selectbox("Focus language", focus_options, index=focus_options.index("Burmese"))
groups = f3.pills("Scripts", list(SCRIPT_GROUPS), selection_mode="multi",
                  default=list(SCRIPT_GROUPS))

scripts = [code for grp in (groups or []) for code in SCRIPT_GROUPS[grp]]
picked = langs[langs["iso_15924"].isin(scripts)]["language"].tolist()
tok_name = NAMES[tok_id]
sel = prem[(prem["tokenizer_id"] == tok_id) & prem["language"].isin(picked)]

twins = {**IDENTICAL, **{v: k for k, v in IDENTICAL.items()}}
if tok_id in twins:
    f1.caption(f"Same counts as {NAMES[twins[tok_id]]}.")

EMPTY = "No scripts selected. Pick at least one above."

# ---------- Charts ----------

a, b = st.columns(2, gap="large")
with a:
    st.subheader("A. Who pays the most?")
    st.caption(f"Tokens for the same text vs English, on {tok_name}.")
    if sel.empty:
        st.info(EMPTY)
    else:
        st.plotly_chart(charts.ranking(sel, focus, c), width="stretch", config=cfg)

with b:
    st.subheader("B. Is it the script?")
    st.caption("On the dashed line, cost follows text size exactly. Grey dots: other tokenizers.")
    if sel.empty:
        st.info(EMPTY)
    else:
        st.plotly_chart(charts.script_vs_tokenizer(prem, tok_id, tok_name, focus, picked, c),
                        width="stretch", config=cfg)

st.subheader("C. Are newer tokenizers fairer?")
st.caption(f"{focus} vs English, oldest tokenizer on the left in each family.")
st.plotly_chart(charts.generations(prem, focus, tok_id, c), width="stretch", config=cfg)

d, notes = st.columns(2, gap="large")
with d:
    st.subheader("D. Fairest tokenizers overall")
    st.caption("How unevenly each tokenizer charges all 15 languages. Left of the dashed line "
               "is fairer than the script alone.")
    st.plotly_chart(charts.fairness(gini, tok_id, c), width="stretch", config=cfg)

with notes:
    st.subheader("What the data can't show")
    st.markdown(f"""
- **Why** tokenizers differ. Training data isn't in our data.
- **Real messages.** {h['n_sents']} translated sentences per language, not real user text.
- **Real bills.** Input tokens at list prices only.
""")
    st.subheader("Sources")
    st.markdown(f"""
- [FLORES+](https://huggingface.co/datasets/openlanguagedata/flores_plus) sentences (CC BY-SA 4.0)
- tiktoken and Hugging Face tokenizers, Anthropic and Google token counting APIs
- `token_premium.csv`, `tokenizer_gini.csv` (see `data_dictionary.md`)
- **Data refreshed {refreshed}**
""")

with st.expander("Data table for charts A and B"):
    if sel.empty:
        st.info(EMPTY)
    else:
        st.dataframe(
            sel.sort_values("premium_vs_en", ascending=False)[[
                "language", "premium_vs_en", "byte_premium_vs_en",
                "mean_tokens_per_sentence", "total_tokens"]],
            hide_index=True, width="stretch",
            column_config={
                "language": "Language",
                "premium_vs_en": st.column_config.NumberColumn("Tokens vs English", format="%.2f×"),
                "byte_premium_vs_en": st.column_config.NumberColumn("Bytes vs English", format="%.2f×"),
                "mean_tokens_per_sentence": st.column_config.NumberColumn("Tokens per sentence", format="%.0f"),
                "total_tokens": st.column_config.NumberColumn("Total tokens", format="%d"),
            },
        )
