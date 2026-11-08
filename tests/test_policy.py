"""The pricing-policy calculations, recomputed here from the raw token counts."""

import numpy as np
import pandas as pd

from src import data
from src.config import ENGLISH

TOKENIZER = "o200k_base"


def raw_premium() -> pd.Series:
    counts = data.load_counts_long()
    totals = counts[counts["tokenizer_id"] == TOKENIZER].groupby("lang_code")["n_tokens"].sum()
    return totals / totals[ENGLISH]


def test_headline_premium_matches_raw_counts() -> None:
    premium = data.load_premium()
    rows = premium[premium["tokenizer_id"] == TOKENIZER].set_index("lang_code")["premium_vs_en"]
    assert np.allclose(rows.sort_index(), raw_premium().sort_index(), atol=1e-4)


def test_buffer_is_quantile_over_average() -> None:
    counts = data.load_counts_long()
    sub = counts[counts["tokenizer_id"] == TOKENIZER].pivot(index="sent_id", columns="lang_code", values="n_tokens")
    ratio = (sub["hin_Deva"] / sub[ENGLISH])
    rows = data.load_premium()
    rows = rows[rows["tokenizer_id"] == TOKENIZER]
    table = data.buffer_table(data.sentence_premiums(counts, TOKENIZER), rows, 0.95).set_index("lang_code")
    assert abs(table.loc["hin_Deva", "covered"] - ratio.quantile(0.95)) < 1e-9
    assert abs(table.loc["hin_Deva", "buffer_pct"] - (ratio.quantile(0.95) / raw_premium()["hin_Deva"] - 1)) < 1e-3
    assert (table["covered"] > table["average"]).all()


def test_tiers_never_undercharge_and_flat_costs_more() -> None:
    rows = data.load_premium()
    rows = rows[(rows["tokenizer_id"] == TOKENIZER) & (rows["lang_code"] != ENGLISH)]
    tiered = data.assign_tiers(rows, data.DEFAULT_TIER_BOUNDS)
    assert (tiered["tier_price"] >= tiered["premium_vs_en"] - 1e-9).all()
    assert (tiered["over_tier"] <= tiered["over_flat"] + 1e-9).all()
    assert set(tiered["tier"]) == {1, 2, 3}
    mix = data.load_mix()
    assert data.weighted_mean(tiered["over_tier"], tiered["lang_code"], mix) < data.weighted_mean(tiered["over_flat"], tiered["lang_code"], mix)


def test_trend_changes_match_the_family_claim() -> None:
    trend = data.trend_table(data.load_gini(), data.load_tokenizers())
    changes = data.family_changes(trend, "gini").set_index("family")
    assert set(changes.index) == {"gpt", "qwen", "gemma", "claude"}
    assert (changes["change"] < -1e-4).sum() == 3 and abs(changes.loc["qwen", "change"]) < 1e-4
    assert trend.groupby("family")["generation_order"].apply(lambda order: order.is_unique).all()


def test_the_most_even_tokeniser_has_the_lowest_one_price_overcharge() -> None:
    premium, counts, mix = data.load_premium(), data.load_counts_long(), data.load_mix()
    gini = data.load_gini().set_index("tokenizer_id")["gini"]
    over = {t: data.compute_pricing_facts(premium, counts, mix, t).over_flat for t in premium["tokenizer_id"].unique()}
    assert min(over, key=over.get) in set(gini[gini == gini.min()].index)


def test_published_values_agree_with_ours() -> None:
    table = data.compare_published(data.load_premium())
    assert len(table) == 11
    assert table["gap_pct"].abs().max() < 0.03
    assert set(table["measure"]) == {"tokens", "bytes"}


def test_default_tier_cutoffs_are_the_best_for_the_default_tokeniser() -> None:
    from src.config import DEFAULT_TOKENIZER, ENGLISH

    premium = data.load_premium()
    rows = premium[(premium["tokenizer_id"] == DEFAULT_TOKENIZER) & (premium["lang_code"] != ENGLISH)]
    best, _ = data.best_tier_bounds(rows, data.load_mix(), data.tier_slider_max(rows))
    tiers = lambda bounds: data.assign_tiers(rows, bounds)["tier"].tolist()
    assert tiers(data.DEFAULT_TIER_BOUNDS) == tiers(best)
