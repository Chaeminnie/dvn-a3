"""Loads the group's processed files and works out the numbers the dashboard shows.

Nothing here edits the data. Every figure on screen is read from, or computed from,
the CSVs in data/, so it can be traced back to a file.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parents[2] / "data"
BASE_LANG = "eng_Latn"

# Readable names for the tokenizer ids used in the CSVs.
NAMES = {
    "gpt2": "GPT-2",
    "cl100k_base": "cl100k (GPT-4)",
    "o200k_base": "o200k (GPT-4o)",
    "qwen2.5": "Qwen 2.5",
    "qwen3": "Qwen 3",
    "gemma2": "Gemma 2",
    "gemma3": "Gemma 3",
    "llama3": "Llama 3.2",
    "mistral_nemo": "Mistral Nemo",
    "claude_haiku_4_5": "Claude Haiku 4.5",
    "claude_sonnet_5_5": "Claude Sonnet 5.5",
    "gemini_3_8_flash": "Gemini 3.8 Flash",
}

# Shorter labels for the small panels in chart C.
SHORT = {
    "gpt2": "GPT-2", "cl100k_base": "cl100k", "o200k_base": "o200k",
    "gemma2": "Gemma 2", "gemma3": "Gemma 3",
    "qwen2.5": "Qwen 2.5", "qwen3": "Qwen 3",
    "claude_haiku_4_5": "Haiku 4.5", "claude_sonnet_5_5": "Sonnet 5.5",
}

# These pairs give the same count on all 3,000 sentences (see data_dictionary.md),
# so charts B and D show each pair once.
IDENTICAL = {"qwen3": "qwen2.5", "gemini_3_8_flash": "gemma3"}

FAMILY_TITLES = {
    "gpt": "OpenAI",
    "gemma": "Google Gemma",
    "qwen": "Alibaba Qwen",
    "claude": "Anthropic Claude",
}


@st.cache_data
def load():
    """Read the files once per session; Streamlit caches the result."""
    prem = pd.read_csv(DATA / "processed" / "token_premium.csv")
    gini = pd.read_csv(DATA / "processed" / "tokenizer_gini.csv")
    langs = pd.read_csv(DATA / "source" / "lang_meta.csv")
    toks = pd.read_csv(DATA / "source" / "tokenizers.csv")
    overhead = pd.read_csv(DATA / "source" / "api_overhead.csv")

    # "Arabic (Modern Standard)" -> "Arabic" so labels fit.
    langs["language"] = langs["language"].str.replace(r"\s*\(.*\)", "", regex=True)

    prem = prem.merge(langs[["lang_code", "language", "iso_15924"]], on="lang_code")
    prem = prem.merge(toks[["tokenizer_id", "family", "generation_order"]], on="tokenizer_id")
    prem["tokenizer"] = prem["tokenizer_id"].map(NAMES)

    gini = gini.merge(toks[["tokenizer_id", "family", "generation_order"]], on="tokenizer_id")
    gini["tokenizer"] = gini["tokenizer_id"].map(NAMES)

    # The last pipeline run is the day the API counts were calibrated.
    refreshed = pd.to_datetime(overhead["calibrated_at"]).max().strftime("%d %b %Y")

    return prem, gini, langs, refreshed


def dedupe(df, joiner=" = "):
    """Drop the second tokenizer of each identical pair and rename the first one."""
    out = df[~df["tokenizer_id"].isin(IDENTICAL)].copy()
    for dup, keep in IDENTICAL.items():
        out.loc[out["tokenizer_id"] == keep, "tokenizer"] = f"{NAMES[keep]}{joiner}{NAMES[dup]}"
    return out


def headline(prem, gini):
    """Whole-dataset facts for the opening screen. Ignores every filter on purpose."""
    others = prem[prem["lang_code"] != BASE_LANG]

    worst = others.loc[others["premium_vs_en"].idxmax()]
    script_max = others.loc[others["byte_premium_vs_en"].idxmax()]

    # The language whose cost depends most on which tokenizer you pick.
    spread = others.groupby("language")["premium_vs_en"].agg(["min", "max"])
    spread["ratio"] = spread["max"] / spread["min"]
    swing_lang = spread["ratio"].idxmax()
    swing = dedupe(others[others["language"] == swing_lang], joiner=" and ")
    lo = swing.loc[swing["premium_vs_en"].idxmin()]
    hi = swing.loc[swing["premium_vs_en"].idxmax()]

    above = (others["premium_vs_en"] > others["byte_premium_vs_en"]).mean()

    fairest = gini.loc[gini["gini"].idxmin()]
    least_fair = gini.loc[gini["gini"].idxmax()]

    return {
        "worst": worst,
        "script_max": script_max,
        "swing_lang": swing_lang,
        "swing_lo": lo,
        "swing_hi": hi,
        "swing_ratio": spread.loc[swing_lang, "ratio"],
        "share_above": above,
        "n_pairs": len(others),
        "n_langs": prem["lang_code"].nunique(),
        "n_toks": prem["tokenizer_id"].nunique(),
        "n_sents": int(prem["n_sentences"].iloc[0]),
        "fairest": fairest,
        "least_fair": least_fair,
        "byte_gini": gini["gini_byte_baseline"].iloc[0],
    }


def family_change(gini):
    """Gini of the oldest and newest tokenizer in each family that has more than one."""
    rows = []
    for fam in FAMILY_TITLES:
        g = gini[gini["family"] == fam].sort_values("generation_order")
        rows.append({
            "family": fam,
            "first": g.iloc[0],
            "last": g.iloc[-1],
            "change": g["gini"].iloc[-1] / g["gini"].iloc[0] - 1,
        })
    return rows
