"""
Token-cost calculator: my dashboard for the A3 group app.

Question : do some languages cost more AI tokens than others?
Persona  : a developer / IT professional outside the English-speaking world
           who is choosing an AI model and estimating costs for their language.

Run from the repo root:   streamlit run calculator.py
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="Token cost calculator", layout="wide")


# ---------------------------------------------------------------------------
# STEP 1: load the three CSVs and join them
#   token_premium.csv : tokens per sentence for every language x tokenizer
#   lang_meta.csv     : turns codes like hin_Deva into "Hindi"
#   prices.csv        : USD per 1M input tokens
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    prem = pd.read_csv(ROOT / "data/processed/token_premium.csv")
    lang = pd.read_csv(ROOT / "data/source/lang_meta.csv")
    prices = pd.read_csv(ROOT / "data/source/prices.csv")
    df = prem.merge(lang[["lang_code", "language"]], on="lang_code", how="left")
    return df, prices


df, prices = load_data()
languages = sorted(df["language"].dropna().unique())
tokenizers = sorted(df["tokenizer_id"].unique())


def default_index(options, wanted):
    return options.index(wanted) if wanted in options else 0


# ---------------------------------------------------------------------------
# STEP 2: the inputs the persona controls (sidebar)
# ---------------------------------------------------------------------------
st.title("How far does your AI budget go in your language?")
st.write(
    "The same sentence is split into more tokens in some languages, and AI is "
    "billed per token. Pick your language, a tokenizer and a budget to see "
    "how much text you can send compared with English."
)

with st.sidebar:
    st.header("Your situation")
    language = st.selectbox(
        "Your language", languages, index=default_index(languages, "Hindi")
    )
    tokenizer = st.selectbox(
        "Tokenizer / model",
        tokenizers,
        index=default_index(tokenizers, "claude_sonnet_5_5"),
    )

    # prices.csv has real prices for some models and an "illustrative" row
    # (tokenizer_id = "all") that works for every tokenizer.
    options = prices[prices["tokenizer_id"].isin([tokenizer, "all"])]
    price_id = st.selectbox("Price source", options["price_id"].tolist())
    price_row = options[options["price_id"] == price_id].iloc[0]
    st.caption(str(price_row["price_note"]))

    price = st.number_input(
        "Input price (USD per 1M tokens)",
        min_value=0.0,
        value=float(price_row["input_usd_per_1m"]),
        step=0.25,
    )
    budget = st.number_input("Budget (USD)", min_value=1.0, value=100.0, step=10.0)

if price <= 0:
    st.warning("Set a price above 0 to see results.")
    st.stop()


# ---------------------------------------------------------------------------
# STEP 3: the calculation
#   tokens for 1 sentence  = mean_tokens_per_sentence (from token_premium.csv)
#   cost of 1 sentence     = tokens x price / 1,000,000
#   sentences for budget   = budget / cost of 1 sentence
# ---------------------------------------------------------------------------
def tokens_per_sentence(lang_name):
    rows = df[(df["language"] == lang_name) & (df["tokenizer_id"] == tokenizer)]
    if rows.empty:
        st.error(f"No data for {lang_name} with {tokenizer}.")
        st.stop()
    return float(rows["mean_tokens_per_sentence"].iloc[0])


def sentences_for_budget(tokens_per_sent):
    return budget / (tokens_per_sent * price / 1_000_000)


tps_you = tokens_per_sentence(language)
tps_en = tokens_per_sentence("English")
sent_you = sentences_for_budget(tps_you)
sent_en = sentences_for_budget(tps_en)
premium = tps_you / tps_en

c1, c2, c3 = st.columns(3)
c1.metric(f"Sentences you can send ({language})", f"{sent_you:,.0f}")
c2.metric("Sentences an English user can send", f"{sent_en:,.0f}")
c3.metric("Token premium vs English", f"{premium:.2f}x")

st.subheader(
    f"With ${budget:,.0f} you get about {sent_you / sent_en:.0%} "
    f"of the text an English speaker gets."
)

# ---------------------------------------------------------------------------
# STEP 4: one sorted bar chart, your language highlighted
# ---------------------------------------------------------------------------
chart_df = df[df["tokenizer_id"] == tokenizer].copy()
chart_df["sentences_for_budget"] = chart_df["mean_tokens_per_sentence"].apply(
    sentences_for_budget
)
chart_df["selected"] = chart_df["language"] == language

chart = (
    alt.Chart(chart_df)
    .mark_bar()
    .encode(
        x=alt.X("sentences_for_budget:Q", title="Sentences you can send for your budget"),
        y=alt.Y("language:N", sort="-x", title=None),
        color=alt.condition("datum.selected", alt.value("#d62728"), alt.value("#9aa5b1")),
        tooltip=[
            alt.Tooltip("language:N"),
            alt.Tooltip("sentences_for_budget:Q", format=",.0f"),
            alt.Tooltip("premium_vs_en:Q", format=".2f", title="premium vs English"),
        ],
    )
)
st.altair_chart(chart, use_container_width=True)

# ---------------------------------------------------------------------------
# STEP 5: verification panel (trace the numbers back to the CSV)
# ---------------------------------------------------------------------------
with st.expander("Verify: where do these numbers come from?"):
    st.write(
        "Source: `data/processed/token_premium.csv`, joined to `lang_meta.csv` "
        "on `lang_code` and to `prices.csv` for the price."
    )
    check = df[
        (df["tokenizer_id"] == tokenizer) & (df["language"].isin([language, "English"]))
    ]
    st.dataframe(
        check[
            [
                "language",
                "tokenizer_id",
                "n_sentences",
                "total_tokens",
                "mean_tokens_per_sentence",
                "premium_vs_en",
            ]
        ],
        hide_index=True,
    )
    st.write(
        f"Premium = {tps_you:.2f} / {tps_en:.2f} = **{premium:.2f}x** "
        "(should match `premium_vs_en` in the table)."
    )
    st.write(
        f"Cost of one {language} sentence = {tps_you:.2f} tokens x ${price} / 1,000,000 "
        f"= ${tps_you * price / 1_000_000:.6f}."
    )
