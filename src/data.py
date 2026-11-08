"""Load, join, check and summarise the committed data package.

The data pipeline that creates the CSV files lives in scripts/ (run it with
`bash run_all.sh`). This module only reads those files. It holds every
calculation behind a number shown in the app, so each number can be traced:

    python -m src.data --validate     check the files against their documented keys
    python -m src.data --facts        print the headline numbers shown on the opening screen
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import pandas as pd

from .config import (
    ENGLISH,
    FAMILY_LABELS,
    PROCESSED_DIR,
    REFERENCE_DIR,
    SOURCE_DIR,
    TOKENIZER_LABELS,
)

# ---------------------------------------------------------------- loaders


def load_langs() -> pd.DataFrame:
    return pd.read_csv(SOURCE_DIR / "lang_meta.csv")


def load_tokenizers() -> pd.DataFrame:
    frame = pd.read_csv(SOURCE_DIR / "tokenizers.csv", parse_dates=["release_date"])
    frame["tokenizer"] = frame["tokenizer_id"].map(TOKENIZER_LABELS)
    frame["family_label"] = frame["family"].map(FAMILY_LABELS)
    return frame


def load_prices() -> pd.DataFrame:
    return pd.read_csv(SOURCE_DIR / "prices.csv", parse_dates=["valid_from", "valid_until", "collected_on"])


def load_mix() -> pd.DataFrame:
    return pd.read_csv(SOURCE_DIR / "language_mix.csv")


def load_gini() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / "tokenizer_gini.csv")


def load_premium() -> pd.DataFrame:
    """token_premium.csv joined to language names, tokenizer labels and families."""
    premium = pd.read_csv(PROCESSED_DIR / "token_premium.csv")
    langs = load_langs()[["lang_code", "language", "iso_15924"]]
    toks = load_tokenizers()[["tokenizer_id", "tokenizer", "family", "family_label", "generation_order", "release_date"]]
    return premium.merge(langs, on="lang_code", how="left", validate="m:1").merge(
        toks, on="tokenizer_id", how="left", validate="m:1"
    )


def load_counts_long() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / "token_counts_long.csv")


def load_flores_sample() -> pd.DataFrame:
    return pd.read_csv(SOURCE_DIR / "flores_sample.csv")


def load_sample_check() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / "sample_vs_full_check.csv")


def load_published() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DIR / "published_premiums.csv", dtype={"tokenizer_id": "string"})


def load_api_collected() -> pd.Series:
    raw = pd.read_csv(SOURCE_DIR / "api_token_counts_raw.csv", usecols=["collected_at"])
    return pd.to_datetime(raw["collected_at"], utc=True)


# ---------------------------------------------------------------- calculations


def tokenizer_summary(premium: pd.DataFrame) -> pd.DataFrame:
    """Per tokenizer: cheapest non-English, median of all 15, costliest language."""
    out = []
    for tokenizer_id, grp in premium.groupby("tokenizer_id"):
        non_en = grp[grp["lang_code"] != ENGLISH]
        top = non_en.loc[non_en["premium_vs_en"].idxmax()]
        low = non_en.loc[non_en["premium_vs_en"].idxmin()]
        out.append(
            {
                "tokenizer_id": tokenizer_id,
                "tokenizer": grp["tokenizer"].iloc[0],
                "min_non_english": float(low["premium_vs_en"]),
                "min_language": low["language"],
                "median_all": float(grp["premium_vs_en"].median()),
                "max_premium": float(top["premium_vs_en"]),
                "max_language": top["language"],
            }
        )
    return pd.DataFrame(out)


def compare_published(premium: pd.DataFrame) -> pd.DataFrame:
    """Our premiums next to the values published by Petrov et al. (2023) for the same languages.

    tokens rows compare against token_premium.csv for the same tokenizer; bytes rows against byte_premium_vs_en
    (identical for every tokenizer, so cl100k_base is used).
    """
    published = load_published()
    ours = premium[premium["tokenizer_id"] == "cl100k_base"].set_index("lang_code")
    published = published.assign(
        ours=[
            ours.loc[row.lang_code, "premium_vs_en" if row.measure == "tokens" else "byte_premium_vs_en"]
            for row in published.itertuples()
        ]
    )
    published["gap"] = published["ours"] - published["published_value"]
    published["gap_pct"] = published["gap"] / published["published_value"]
    published["language"] = published["lang_code"].map(ours["language"])
    return published


# ---------------------------------------------------------------- pricing policy

COVERAGE_LEVELS = (0.80, 0.90, 0.95)
DEFAULT_COVERAGE = 0.95
# Default tier cut-offs: the pair with the lowest average overcharge on the default tokeniser (o200k, all 14 languages),
# so the dashboard opens on the tiers that show the benefit of tiering best. tests/test_policy.py checks this against best_tier_bounds().
DEFAULT_TIER_BOUNDS = (1.5, 2.1)


def sentence_premiums(counts: pd.DataFrame, tokenizer_id: str) -> pd.DataFrame:
    """Per-sentence premium: tokens of a sentence in a language / tokens of the same sentence in English.

    FLORES+ sentences are parallel (same sent_id in every language), so the
    ratio compares the same content. English itself is excluded (always 1.0).
    """
    sub = counts[counts["tokenizer_id"] == tokenizer_id]
    wide = sub.pivot(index="sent_id", columns="lang_code", values="n_tokens")
    ratio = wide.drop(columns=ENGLISH).div(wide[ENGLISH], axis=0)
    out = ratio.reset_index().melt(id_vars="sent_id", var_name="lang_code", value_name="premium")
    return out.dropna()


def buffer_table(sentences: pd.DataFrame, premium_rows: pd.DataFrame, coverage: float) -> pd.DataFrame:
    """Spread of the per-sentence premium and the buffer needed to cover `coverage` of sentences.

    `average` is the aggregate premium from token_premium.csv (total tokens / English total).
    `covered` is the premium that at least `coverage` of the sentences needed or less.
    `buffer_pct` = covered / average - 1.
    """
    q = sentences.groupby("lang_code")["premium"].quantile([0.05, 0.25, 0.5, 0.75, coverage]).unstack()
    assert coverage > 0.75, "coverage must be above the 75th percentile"
    q.columns = ["p05", "p25", "p50", "p75", "covered"]
    q = q.reset_index()
    base = premium_rows[["lang_code", "language", "iso_15924", "premium_vs_en"]].rename(columns={"premium_vs_en": "average"})
    out = q.merge(base, on="lang_code", how="inner", validate="1:1")
    out["buffer_pct"] = out["covered"] / out["average"] - 1.0
    return out


def assign_tiers(rows: pd.DataFrame, bounds: tuple[float, float]) -> pd.DataFrame:
    """Tier 1 up to bounds[0], tier 2 up to bounds[1], tier 3 above. Tier price = costliest language in the tier.

    `rows` are the non-English languages: English is the reference (price 1.0x) and is never tiered.
    """
    out = rows.copy()
    out["tier"] = 1 + (out["premium_vs_en"] > bounds[0]).astype(int) + (out["premium_vs_en"] > bounds[1]).astype(int)
    out["tier_price"] = out.groupby("tier")["premium_vs_en"].transform("max")
    out["flat_price"] = out["premium_vs_en"].max()
    out["over_tier"] = out["tier_price"] / out["premium_vs_en"] - 1.0
    out["over_flat"] = out["flat_price"] / out["premium_vs_en"] - 1.0
    return out


def weighted_mean(values: pd.Series, lang_codes: pd.Series, mix: pd.DataFrame) -> float:
    """Mean of `values` weighted by language_mix.csv user_share, renormalised to the languages present."""
    weights = lang_codes.map(mix.set_index("lang_code")["user_share"]).astype(float)
    return float((values * weights).sum() / weights.sum())


def tier_slider_max(rows: pd.DataFrame) -> float:
    """Upper end of the tier cut-off slider: the costliest language's premium rounded up (never below 3.0).

    A cut-off above the costliest language's premium puts every language in the lower tiers, so it has no use.
    """
    import math

    return max(3.0, float(math.ceil(float(rows["premium_vs_en"].max()))))


def best_tier_bounds(rows: pd.DataFrame, mix: pd.DataFrame, upper: float, step: float = 0.1) -> tuple[tuple[float, float], float]:
    """Cut-offs (on the slider's grid) that give the lowest average overcharge with three tiers.

    Every pair of cut-offs from 1.0 to `upper` is tried. The average overcharge is weighted like the dashboard's
    (language_mix.csv, renormalised to the languages present). Ties go to the lowest cut-offs, which sit just above
    a language's premium. Returns ((cut-off 1, cut-off 2), average overcharge).
    """
    import numpy as np

    premium = rows["premium_vs_en"].to_numpy(float)
    weight = rows["lang_code"].map(mix.set_index("lang_code")["user_share"]).astype(float).to_numpy()
    grid = np.round(np.arange(1.0, upper + step / 2, step), 4)
    best: tuple[float, tuple[float, float]] | None = None
    for i, first in enumerate(grid):
        for second in grid[i:]:
            tier = 1 + (premium > first).astype(int) + (premium > second).astype(int)
            price = np.zeros_like(premium)
            for t in (1, 2, 3):
                inside = tier == t
                if inside.any():
                    price[inside] = premium[inside].max()
            over = float(((price / premium - 1.0) * weight).sum() / weight.sum())
            if best is None or over < best[0] - 1e-12:
                best = (over, (round(float(first), 1), round(float(second), 1)))
    assert best is not None
    return best[1], best[0]


TREND_MEASURES = {
    "gini": "Inequality across languages (Gini)",
    "max_premium": "Costliest language's premium (× English)",
    "median_premium": "Median language's premium (× English)",
}


def trend_table(gini: pd.DataFrame, tokenizers: pd.DataFrame) -> pd.DataFrame:
    """One row per tokeniser with its family, version order and the three trend measures.

    `n_versions` is how many tokenisers the family has, so callers can keep only families that can show a change.
    `costliest_language` is the language behind `max_premium`.
    """
    langs = load_langs().set_index("lang_code")["language"]
    frame = tokenizers[["tokenizer_id", "tokenizer", "family", "family_label", "generation_order", "release_date"]].merge(
        gini[["tokenizer_id", "gini", "max_premium", "max_premium_lang", "median_premium"]], on="tokenizer_id", validate="1:1"
    )
    frame["costliest_language"] = frame["max_premium_lang"].map(langs)
    frame["n_versions"] = frame.groupby("family")["tokenizer_id"].transform("size")
    return frame.sort_values(["family", "generation_order"]).reset_index(drop=True)


def family_changes(trend: pd.DataFrame, measure: str) -> pd.DataFrame:
    """First and newest version of each family on one measure: the change that the trend story reports."""
    rows = []
    for family, grp in trend[trend["n_versions"] > 1].groupby("family"):
        grp = grp.sort_values("generation_order")
        first, last = grp.iloc[0], grp.iloc[-1]
        rows.append(
            {
                "family": family,
                "family_label": first["family_label"],
                "first": first["tokenizer"],
                "last": last["tokenizer"],
                "first_value": float(first[measure]),
                "last_value": float(last[measure]),
                "change": float(last[measure]) / float(first[measure]) - 1.0,
            }
        )
    return pd.DataFrame(rows).sort_values("change").reset_index(drop=True)


@dataclass(frozen=True)
class PricingFacts:
    tokenizer: str
    coverage: float
    costliest_language: str
    costliest_premium: float
    buffer_low: float
    buffer_low_language: str
    buffer_high: float
    buffer_high_language: str
    tier_bounds: tuple[float, float]
    over_flat: float
    over_tier: float
    tier_prices: tuple[float, float, float]
    tier_sizes: tuple[int, int, int]
    latin_total: int
    latin_in_tier1: int
    non_latin_in_tier1: int
    non_latin_total: int


def compute_pricing_facts(
    premium: pd.DataFrame, counts: pd.DataFrame, mix: pd.DataFrame, tokenizer_id: str,
    coverage: float = DEFAULT_COVERAGE, bounds: tuple[float, float] = DEFAULT_TIER_BOUNDS,
) -> PricingFacts:
    rows = premium[premium["tokenizer_id"] == tokenizer_id]
    non_en = rows[rows["lang_code"] != ENGLISH]  # English is the reference price (1.0x), so it is not tiered
    top = non_en.loc[non_en["premium_vs_en"].idxmax()]
    buf = buffer_table(sentence_premiums(counts, tokenizer_id), non_en, coverage)
    lo = buf.loc[buf["buffer_pct"].idxmin()]
    hi = buf.loc[buf["buffer_pct"].idxmax()]
    tiers = assign_tiers(non_en, bounds)
    prices = tiers.groupby("tier")["tier_price"].first().reindex([1, 2, 3])
    sizes = tiers.groupby("tier").size().reindex([1, 2, 3], fill_value=0)
    latin = tiers[tiers["iso_15924"] == "Latn"]
    other = tiers[tiers["iso_15924"] != "Latn"]
    return PricingFacts(
        tokenizer=TOKENIZER_LABELS[tokenizer_id],
        coverage=coverage,
        costliest_language=top["language"],
        costliest_premium=float(top["premium_vs_en"]),
        buffer_low=float(lo["buffer_pct"]),
        buffer_low_language=lo["language"],
        buffer_high=float(hi["buffer_pct"]),
        buffer_high_language=hi["language"],
        tier_bounds=bounds,
        over_flat=weighted_mean(tiers["over_flat"], tiers["lang_code"], mix),
        over_tier=weighted_mean(tiers["over_tier"], tiers["lang_code"], mix),
        tier_prices=tuple(float(p) if pd.notna(p) else float("nan") for p in prices),
        tier_sizes=tuple(int(n) for n in sizes),
        latin_total=len(latin),
        latin_in_tier1=int((latin["tier"] == 1).sum()),
        non_latin_in_tier1=int((other["tier"] == 1).sum()),
        non_latin_total=len(other),
    )


@dataclass(frozen=True)
class BufferRange:
    """Buffer to cover `coverage` of sentences, across every tokenizer (not just the default one)."""

    coverage: float
    n_tokenizers: int
    low: float
    low_language: str
    low_tokenizer: str
    high: float
    high_language: str
    high_tokenizer: str


def compute_buffer_range(premium: pd.DataFrame, counts: pd.DataFrame, coverage: float = DEFAULT_COVERAGE) -> BufferRange:
    frames = []
    for tokenizer_id in premium["tokenizer_id"].unique():
        rows = premium[(premium["tokenizer_id"] == tokenizer_id) & (premium["lang_code"] != ENGLISH)]
        table = buffer_table(sentence_premiums(counts, tokenizer_id), rows, coverage)
        frames.append(table.assign(tokenizer_id=tokenizer_id))
    every = pd.concat(frames, ignore_index=True)
    lo = every.loc[every["buffer_pct"].idxmin()]
    hi = every.loc[every["buffer_pct"].idxmax()]
    return BufferRange(
        coverage=coverage,
        n_tokenizers=int(every["tokenizer_id"].nunique()),
        low=float(lo["buffer_pct"]),
        low_language=str(lo["language"]),
        low_tokenizer=TOKENIZER_LABELS[lo["tokenizer_id"]],
        high=float(hi["buffer_pct"]),
        high_language=str(hi["language"]),
        high_tokenizer=TOKENIZER_LABELS[hi["tokenizer_id"]],
    )


@dataclass(frozen=True)
class AllTokenisers:
    """Pricing results at the default settings (95% coverage, the default tier cut-offs) on every tokeniser."""

    n_tokenizers: int
    tiers_beat_flat_on: int  # tokenisers where three tiers overcharge less than one price
    over_flat_low: float
    over_flat_high: float
    over_tier_low: float
    over_tier_high: float


def compute_all_tokenisers(premium: pd.DataFrame, counts: pd.DataFrame, mix: pd.DataFrame) -> AllTokenisers:
    results = [compute_pricing_facts(premium, counts, mix, tokenizer_id) for tokenizer_id in premium["tokenizer_id"].unique()]
    return AllTokenisers(
        n_tokenizers=len(results),
        tiers_beat_flat_on=sum(r.over_tier < r.over_flat for r in results),
        over_flat_low=min(r.over_flat for r in results),
        over_flat_high=max(r.over_flat for r in results),
        over_tier_low=min(r.over_tier for r in results),
        over_tier_high=max(r.over_tier for r in results),
    )



# ---------------------------------------------------------------- facts


@dataclass(frozen=True)
class Facts:
    n_tokenizers: int
    n_languages: int
    n_sentences: int
    english_cheapest_on: int
    costliest_language: str
    costliest_language_count: int
    other_costliest: str
    costliest_elsewhere: str  # tokenisers where another language is costliest (tied tokenisers listed once)
    costliest_low: float  # premium of costliest_language, lowest and highest across tokenisers
    costliest_high: float
    min_premium: float
    min_premium_language: str
    min_premium_tokenizer: str
    max_premium: float
    max_premium_language: str
    max_premium_tokenizer: str
    gini_min: float
    gini_min_tokenizer: str
    gini_max: float
    gini_max_tokenizer: str
    swing_language: str
    swing_ratio: float
    swing_low: float
    swing_low_tokenizer: str
    swing_high: float
    swing_high_tokenizer: str
    families_multi: int
    families_fairer: tuple[tuple[str, float, float], ...]
    families_flat: tuple[tuple[str, float], ...]
    fairest_tokenizer: str
    fairest_max_premium: float
    fairest_max_language: str
    byte_gini: float


def _tied(frame: pd.DataFrame, column: str, value: float, label: str) -> str:
    """All labels whose value equals `value` (identical tokenizers tie on counts)."""
    hits = frame[(frame[column] - value).abs() < 1e-9][label]
    return " / ".join(dict.fromkeys(hits))


def compute_facts(premium: pd.DataFrame, gini: pd.DataFrame, tokenizers: pd.DataFrame) -> Facts:
    non_en = premium[premium["lang_code"] != ENGLISH]
    gini = gini.assign(tokenizer=gini["tokenizer_id"].map(TOKENIZER_LABELS))
    cheapest_en = int(
        (premium.groupby("tokenizer_id")["premium_vs_en"].min() == 1.0).sum()
    )
    # English is the cheapest language on a tokenizer when no other language is below 1.0.
    english_cheapest = int(
        (non_en.groupby("tokenizer_id")["premium_vs_en"].min() >= 1.0).sum()
    )
    assert cheapest_en >= english_cheapest

    top_langs = gini["max_premium_lang"].value_counts()
    langs = load_langs().set_index("lang_code")["language"]
    top = top_langs.index[0]
    others = [langs[code] for code in top_langs.index[1:]]

    lo = non_en.loc[non_en["premium_vs_en"].idxmin()]
    hi = non_en.loc[non_en["premium_vs_en"].idxmax()]
    g_lo = gini.loc[gini["gini"].idxmin()]
    g_hi = gini.loc[gini["gini"].idxmax()]

    spread = non_en.groupby("language")["premium_vs_en"].agg(["min", "max"])
    spread["ratio"] = spread["max"] / spread["min"]
    swing_lang = spread["ratio"].idxmax()
    swing_rows = non_en[non_en["language"] == swing_lang]
    s_lo = swing_rows.loc[swing_rows["premium_vs_en"].idxmin()]
    s_hi = swing_rows.loc[swing_rows["premium_vs_en"].idxmax()]

    merged = tokenizers.merge(gini[["tokenizer_id", "gini"]], on="tokenizer_id")
    fairer, flat = [], []
    multi = 0
    for family, grp in merged.groupby("family"):
        if len(grp) < 2:
            continue
        multi += 1
        grp = grp.sort_values("generation_order")
        first, last = float(grp["gini"].iloc[0]), float(grp["gini"].iloc[-1])
        label = FAMILY_LABELS[family]
        if last < first - 1e-4:
            fairer.append((label, first, last))
        else:
            flat.append((label, first))

    fairest = g_lo["tokenizer_id"]  # tied tokenizers have identical counts, so any one gives the same row
    fairest_rows = non_en[non_en["tokenizer_id"] == fairest]
    fr = fairest_rows.loc[fairest_rows["premium_vs_en"].idxmax()]

    per_tokenizer_top = non_en.loc[non_en.groupby("tokenizer_id")["premium_vs_en"].idxmax()]
    elsewhere = per_tokenizer_top[per_tokenizer_top["language"] != langs[top]]
    top_rows = non_en[non_en["language"] == langs[top]]

    return Facts(
        n_tokenizers=int(premium["tokenizer_id"].nunique()),
        n_languages=int(premium["lang_code"].nunique()),
        n_sentences=int(premium["n_sentences"].iloc[0]),
        english_cheapest_on=english_cheapest,
        costliest_language=langs[top],
        costliest_language_count=int(top_langs.iloc[0]),
        other_costliest=" and ".join(others),
        costliest_elsewhere=" and ".join(sorted(elsewhere["tokenizer"].unique())),
        costliest_low=float(top_rows["premium_vs_en"].min()),
        costliest_high=float(top_rows["premium_vs_en"].max()),
        min_premium=float(lo["premium_vs_en"]),
        min_premium_language=lo["language"],
        min_premium_tokenizer=_tied(
            non_en[non_en["language"] == lo["language"]], "premium_vs_en", float(lo["premium_vs_en"]), "tokenizer"
        ),
        max_premium=float(hi["premium_vs_en"]),
        max_premium_language=hi["language"],
        max_premium_tokenizer=_tied(
            non_en[non_en["language"] == hi["language"]], "premium_vs_en", float(hi["premium_vs_en"]), "tokenizer"
        ),
        gini_min=float(g_lo["gini"]),
        gini_min_tokenizer=_tied(gini, "gini", float(g_lo["gini"]), "tokenizer"),
        gini_max=float(g_hi["gini"]),
        gini_max_tokenizer=_tied(gini, "gini", float(g_hi["gini"]), "tokenizer"),
        swing_language=swing_lang,
        swing_ratio=float(spread.loc[swing_lang, "ratio"]),
        swing_low=float(s_lo["premium_vs_en"]),
        swing_low_tokenizer=_tied(swing_rows, "premium_vs_en", float(s_lo["premium_vs_en"]), "tokenizer"),
        swing_high=float(s_hi["premium_vs_en"]),
        swing_high_tokenizer=_tied(swing_rows, "premium_vs_en", float(s_hi["premium_vs_en"]), "tokenizer"),
        families_multi=multi,
        families_fairer=tuple(fairer),
        families_flat=tuple(flat),
        fairest_tokenizer=_tied(gini, "gini", float(g_lo["gini"]), "tokenizer"),
        fairest_max_premium=float(fr["premium_vs_en"]),
        fairest_max_language=fr["language"],
        byte_gini=float(gini["gini_byte_baseline"].iloc[0]),
    )


# ---------------------------------------------------------------- validation


def validate() -> list[str]:
    """Return a list of problems; an empty list means the package is consistent."""
    problems: list[str] = []
    premium = pd.read_csv(PROCESSED_DIR / "token_premium.csv")
    gini = load_gini()
    langs = load_langs()
    toks = load_tokenizers()
    prices = load_prices()
    mix = load_mix()

    if premium.duplicated(["lang_code", "tokenizer_id"]).any():
        problems.append("token_premium.csv: duplicate (lang_code, tokenizer_id)")
    if len(premium) != len(langs) * len(toks):
        problems.append(f"token_premium.csv: {len(premium)} rows, expected {len(langs) * len(toks)}")
    if set(premium["lang_code"]) != set(langs["lang_code"]):
        problems.append("token_premium.csv: language codes differ from lang_meta.csv")
    if set(premium["tokenizer_id"]) != set(toks["tokenizer_id"]):
        problems.append("token_premium.csv: tokenizer ids differ from tokenizers.csv")
    english = premium[premium["lang_code"] == ENGLISH]["premium_vs_en"]
    if not ((english - 1.0).abs() < 1e-9).all():
        problems.append("token_premium.csv: English premium is not 1.0")
    if premium["n_sentences"].nunique() != 1:
        problems.append("token_premium.csv: unequal sentence counts")
    if premium[["premium_vs_en", "byte_premium_vs_en"]].isna().any().any():
        problems.append("token_premium.csv: missing premium values")

    if gini["tokenizer_id"].duplicated().any() or set(gini["tokenizer_id"]) != set(toks["tokenizer_id"]):
        problems.append("tokenizer_gini.csv: tokenizer ids differ from tokenizers.csv")
    summary = tokenizer_summary(load_premium()).set_index("tokenizer_id")
    check = gini.set_index("tokenizer_id")
    if not ((summary["median_all"] - check["median_premium"]).abs() < 1e-3).all():
        problems.append("tokenizer_gini.csv: median_premium does not match token_premium.csv")
    if not ((summary["max_premium"] - check["max_premium"]).abs() < 1e-3).all():
        problems.append("tokenizer_gini.csv: max_premium does not match token_premium.csv")

    known = set(toks["tokenizer_id"]) | {"all"}
    if not set(prices["tokenizer_id"]).issubset(known):
        problems.append("prices.csv: unknown tokenizer_id")
    if prices["price_id"].duplicated().any():
        problems.append("prices.csv: duplicate price_id")
    if abs(mix["user_share"].sum() - 1.0) > 0.001:
        problems.append("language_mix.csv: shares do not sum to 1 within 0.001")
    if set(mix["lang_code"]) != set(langs["lang_code"]):
        problems.append("language_mix.csv: language codes differ from lang_meta.csv")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", action="store_true", help="Check the data package and stop")
    parser.add_argument("--facts", action="store_true", help="Print the headline numbers")
    args = parser.parse_args()
    if args.validate or not args.facts:
        problems = validate()
        if problems:
            sys.exit("Data package problems:\n- " + "\n- ".join(problems))
        print("Data package valid")
    if args.facts:
        facts = compute_facts(load_premium(), load_gini(), load_tokenizers())
        for key, value in facts.__dict__.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
