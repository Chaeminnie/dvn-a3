"""Cost vs English: token premium per language and tokenizer.

Put this file in the root of the dvn-a3 repo (next to README.md) and run:
    streamlit run chart_cost_vs_english.py
Needs: pip install streamlit plotly pandas
"""
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

PREMIUM_FILE = "data/processed/token_premium.csv"   # one row per language x tokenizer
LONG_FILE = "data/processed/token_counts_long.csv"  # one row per sentence x language x tokenizer

LANG_NAMES = {
    "eng_Latn": "English", "mya_Mymr": "Burmese", "tam_Taml": "Tamil",
    "amh_Ethi": "Amharic", "hin_Deva": "Hindi", "tha_Thai": "Thai",
    "arb_Arab": "Arabic", "rus_Cyrl": "Russian", "kor_Hang": "Korean",
    "jpn_Jpan": "Japanese", "swh_Latn": "Swahili", "cmn_Hans": "Chinese",
    "fra_Latn": "French", "deu_Latn": "German", "spa_Latn": "Spanish",
}
TOKENIZER_NAMES = {
    "gpt2": "GPT-2", "cl100k_base": "cl100k (GPT-4)", "o200k_base": "o200k (GPT-4o)",
    "qwen2.5": "Qwen2.5", "qwen3": "Qwen3", "gemma2": "Gemma 2", "gemma3": "Gemma 3",
    "llama3": "Llama 3.2", "mistral_nemo": "Mistral Nemo",
    "claude_haiku_4_5": "Claude Haiku 4.5", "claude_sonnet_5_5": "Claude Sonnet 5.5",
    "gemini_3_8_flash": "Gemini 3.8 Flash",
}

st.set_page_config(page_title="Cost vs English", layout="wide")
st.title("Cost vs English")
st.markdown(
    "**How many times more tokens does the same sentence need than in English?** "
    "Each cell is one language on one tokenizer. English = 1.0. "
    "Based on the same 200 FLORES+ sentences in every language."
)

df = pd.read_csv(PREMIUM_FILE)
df["Language"] = df["lang_code"].map(LANG_NAMES).fillna(df["lang_code"])
df["Tokenizer"] = df["tokenizer_id"].map(TOKENIZER_NAMES).fillna(df["tokenizer_id"])

# Sort: most expensive language at the top, fairest tokenizer on the left
lang_order = df.groupby("Language")["premium_vs_en"].mean().sort_values(ascending=False).index
tok_order = df.groupby("Tokenizer")["premium_vs_en"].mean().sort_values().index
grid = df.pivot(index="Language", columns="Tokenizer", values="premium_vs_en").loc[lang_order, tok_order]

# Heatmap, coloured on a log scale so 1.5x and 17x are both readable
fig = px.imshow(np.log10(grid), x=list(grid.columns), y=list(grid.index),
                color_continuous_scale="Reds", aspect="auto")
fig.update_traces(
    text=grid.values,
    texttemplate="%{text:.1f}x",
    hovertemplate="%{y} on %{x}: %{text:.2f}x English<extra></extra>",
)
ticks = [1, 2, 5, 10, 20]
fig.update_coloraxes(cmin=0, cmax=np.log10(20), colorbar=dict(
    title="x English", tickvals=np.log10(ticks), ticktext=[f"{t}x" for t in ticks]))
fig.update_layout(height=620, xaxis_title="Tokenizer (fairest on the left)", yaxis_title=None,
                  xaxis_side="top", margin=dict(t=80))
st.plotly_chart(fig, use_container_width=True)
st.caption(f"Source: {PREMIUM_FILE}, column premium_vs_en "
           "(total tokens for the language / total tokens for English, same tokenizer).")

# Absolute tokens next to ratios: a ratio can look small just because English got more expensive
st.subheader("Actual tokens per sentence")
tok = st.selectbox("Tokenizer", list(tok_order), index=list(tok_order).index("GPT-2"))
one = df[df["Tokenizer"] == tok].sort_values("mean_tokens_per_sentence")
bar = px.bar(one, x="mean_tokens_per_sentence", y="Language", orientation="h",
             text=one["mean_tokens_per_sentence"].round(0).astype(int),
             labels={"mean_tokens_per_sentence": "Mean tokens per sentence", "Language": ""},
             color_discrete_sequence=["#c0392b"])
bar.update_layout(height=520)
st.plotly_chart(bar, use_container_width=True)

# Verification: recompute one premium from the raw per-sentence counts
with st.expander("Check a number against the raw data"):
    lang = st.selectbox("Language", list(lang_order))
    raw = pd.read_csv(LONG_FILE)
    code = df.loc[df["Language"] == lang, "lang_code"].iloc[0]
    tok_id = df.loc[df["Tokenizer"] == tok, "tokenizer_id"].iloc[0]
    rows = raw[raw["tokenizer_id"] == tok_id]
    lang_rows = rows[rows["lang_code"] == code]
    eng_rows = rows[rows["lang_code"] == "eng_Latn"]
    lang_total, eng_total = lang_rows["n_tokens"].sum(), eng_rows["n_tokens"].sum()
    shown = df.loc[(df["Tokenizer"] == tok) & (df["Language"] == lang), "premium_vs_en"].iloc[0]

    st.write(f"Raw file: `{LONG_FILE}`, filtered to tokenizer_id = `{tok_id}`")
    st.write(f"1. Sum of n_tokens for {lang} (`{code}`), {len(lang_rows)} sentences: **{lang_total:,}**")
    st.write(f"2. Sum of n_tokens for English (`eng_Latn`), {len(eng_rows)} sentences: **{eng_total:,}**")
    st.write(f"3. {lang_total:,} / {eng_total:,} = **{lang_total / eng_total:.4f}**")
    st.write(f"Value in `{PREMIUM_FILE}` and in the heatmap: **{shown:.4f}**")
    st.dataframe(lang_rows.head(10), use_container_width=True)
