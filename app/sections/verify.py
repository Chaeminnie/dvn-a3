"""Footer: check a number against the raw data, plus the limitations list. Owner: Advait.

Traces the premium for the sidebar's tokenizer and focus language back to the per-sentence counts.
"""
import pandas as pd
import streamlit as st

import data
import style


@st.cache_data
def _long() -> pd.DataFrame:
    return pd.read_csv(data.PROC / "token_counts_long.csv", usecols=["lang_code", "tokenizer_id", "n_tokens"])


def render(state):
    prem = state.d["prem"]
    tok, tok_name = state.tokenizer, data.TOKENIZER[state.tokenizer]
    row = prem[(prem["tokenizer_id"] == tok) & (prem["language"] == state.focus)]
    if row.empty:
        st.caption(f"No data for {state.focus} on {tok_name}.")
        return
    row = row.iloc[0]
    code = row["lang_code"]

    raw = _long()
    raw = raw[raw["tokenizer_id"] == tok]
    lang = raw.loc[raw["lang_code"] == code, "n_tokens"]
    eng = raw.loc[raw["lang_code"] == data.ENGLISH, "n_tokens"]
    recomputed = lang.sum() / eng.sum()
    shown = row["premium_vs_en"]

    st.markdown(f"**{state.focus} on {tok_name}** is shown as **{style.fmt_x(shown)}**. Recomputing it:")
    st.markdown(
        f"1. Open `data/processed/token_counts_long.csv` and keep rows where `tokenizer_id = {tok}`.\n"
        f"2. Sum `n_tokens` for `lang_code = {code}` ({len(lang)} sentences): **{lang.sum():,}**\n"
        f"3. Sum `n_tokens` for `lang_code = {data.ENGLISH}` ({len(eng)} sentences): **{eng.sum():,}**\n"
        f"4. {lang.sum():,} ÷ {eng.sum():,} = **{recomputed:.4f}**"
    )
    if abs(recomputed - shown) < 5e-4:
        st.success(f"Matches `token_premium.csv`, column `premium_vs_en` = {shown:.4f}.", icon=":material/check:")
    else:
        st.error(f"Does not match `token_premium.csv` ({shown:.4f}).", icon=":material/error:")
    st.caption("Change the tokenizer or focus language in the sidebar to trace another number.")


def limitations():
    st.markdown(
        "- **15 languages** chosen by the team. The Gini and the rankings depend on this set.\n"
        "- **200-sentence sample** of FLORES+ devtest; the largest sample-vs-full difference we measured was 3.13%.\n"
        "- **Translated text.** FLORES+ is professionally translated news-style text, not real user messages.\n"
        "- **Token counts and list prices only.** Input tokens only; no discounts, caching or output tokens.\n"
        "- **Language mix** (`language_mix.csv`) is an equal-weight placeholder, not real usage data.\n"
        "- **Duplicate tokenizers.** Qwen 3 = Qwen 2.5 and Gemini 3.8 Flash = Gemma 3 give identical counts, "
        "so they are not independent data points.\n"
        "- **Release dates.** Llama 3.2 uses the Llama 3 tokenizer release date; that it reuses that tokenizer "
        "was not verified."
    )
