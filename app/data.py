"""Data loading and labels shared by all tabs (based on Chandan's loaders.py).
All numbers come from the CSVs in data/."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "source"
PROC = ROOT / "data" / "processed"
ENGLISH = "eng_Latn"

QUESTION = ("Is the extra token cost of non-English languages a fixed property of their scripts, "
            "or a result of tokenizer design choices that is shrinking?")
PERSONA = ("AI pricing lead deciding whether to absorb the extra cost, adjust plans and quotas, "
           "or switch to a fairer model")

TOKENIZER = {
    "gpt2": "GPT-2", "cl100k_base": "GPT-4 (cl100k)", "o200k_base": "GPT-4o (o200k)",
    "qwen2.5": "Qwen 2.5", "qwen3": "Qwen 3", "gemma2": "Gemma 2", "gemma3": "Gemma 3",
    "llama3": "Llama 3.2", "mistral_nemo": "Mistral Nemo",
    "claude_haiku_4_5": "Claude Haiku 4.5", "claude_sonnet_5_5": "Claude Sonnet 5.5",
    "gemini_3_8_flash": "Gemini 3.8 Flash",
}
FAMILY = {"gpt": "OpenAI GPT", "gemma": "Google Gemma", "qwen": "Alibaba Qwen", "claude": "Anthropic Claude",
          "llama": "Meta Llama", "mistral": "Mistral", "gemini": "Google Gemini"}
# These pairs give identical counts on all sentences (data_dictionary.md).
IDENTICAL = {"qwen3": "qwen2.5", "gemini_3_8_flash": "gemma3"}
SCRIPT_GROUPS = {
    "Latin": ["Latn"],
    "Other alphabets": ["Cyrl", "Arab", "Hang", "Ethi"],
    "South & Southeast Asian": ["Deva", "Taml", "Thai", "Mymr"],
    "Chinese & Japanese": ["Hans", "Jpan"],
}


@st.cache_data
def load() -> dict:
    prem = pd.read_csv(PROC / "token_premium.csv")
    gini = pd.read_csv(PROC / "tokenizer_gini.csv")
    langs = pd.read_csv(SRC / "lang_meta.csv")
    toks = pd.read_csv(SRC / "tokenizers.csv", parse_dates=["release_date"])
    prices = pd.read_csv(SRC / "prices.csv")
    mix = pd.read_csv(SRC / "language_mix.csv")
    overhead = pd.read_csv(SRC / "api_overhead.csv")

    langs["language"] = langs["language"].str.replace(r"\s*\(.*\)", "", regex=True)  # "Arabic (Modern Standard)" -> "Arabic"
    tcols = ["tokenizer_id", "family", "generation_order", "release_date"]
    prem = prem.merge(langs[["lang_code", "language", "iso_15924"]], on="lang_code").merge(toks[tcols], on="tokenizer_id")
    prem["tokenizer"] = prem["tokenizer_id"].map(TOKENIZER)
    gini = gini.merge(toks[tcols], on="tokenizer_id")
    gini["tokenizer"] = gini["tokenizer_id"].map(TOKENIZER)
    refreshed = pd.to_datetime(overhead["calibrated_at"]).max().strftime("%d %b %Y")
    return dict(prem=prem, gini=gini, langs=langs, toks=toks, prices=prices, mix=mix, refreshed=refreshed)


def dedupe(df: pd.DataFrame, joiner: str = " = ") -> pd.DataFrame:
    """Show each identical tokenizer pair once."""
    out = df[~df["tokenizer_id"].isin(IDENTICAL)].copy()
    for dup, keep in IDENTICAL.items():
        out.loc[out["tokenizer_id"] == keep, "tokenizer"] = f"{TOKENIZER[keep]}{joiner}{TOKENIZER[dup]}"
    return out


def headline(prem: pd.DataFrame, gini: pd.DataFrame) -> dict:
    """Whole-dataset numbers for the overview (not affected by filters)."""
    others = prem[prem["lang_code"] != ENGLISH]
    worst = others.loc[others["premium_vs_en"].idxmax()]
    spread = others.groupby("language")["premium_vs_en"].agg(["min", "max"])
    spread["ratio"] = spread["max"] / spread["min"]
    swing_lang = spread["ratio"].idxmax()
    return dict(
        worst=worst,
        swing_lang=swing_lang,
        swing_lo=spread.loc[swing_lang, "min"],
        swing_hi=spread.loc[swing_lang, "max"],
        share_above=(others["premium_vs_en"] > others["byte_premium_vs_en"]).mean(),
        n_pairs=len(others),
        n_langs=prem["lang_code"].nunique(),
        n_toks=prem["tokenizer_id"].nunique(),
        n_sents=int(prem["n_sentences"].iloc[0]),
        fairest=gini.loc[gini["gini"].idxmin()],
    )


def family_change(gini: pd.DataFrame) -> pd.DataFrame:
    """Oldest vs newest tokenizer Gini in each family that has two or more."""
    rows = []
    for fam, g in gini.groupby("family"):
        if len(g) < 2:
            continue
        g = g.sort_values("release_date")
        a, b = g.iloc[0], g.iloc[-1]
        rows.append(dict(family=fam, first=a["tokenizer"], last=b["tokenizer"],
                         gini_first=a["gini"], gini_last=b["gini"], change=b["gini"] / a["gini"] - 1))
    return pd.DataFrame(rows)
