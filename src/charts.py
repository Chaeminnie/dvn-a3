"""Altair chart builders. One function per chart; each takes tidy data frames.

Design choices (what each chart is for, and what was rejected) are recorded in
the docstrings so they can be quoted when the design is explained.

Colour: one hue for single-series charts. Where colour carries identity it
follows the entity (family or language) in a fixed slot order from the
validated palette in config.SERIES, so filtering never repaints the survivors.
Value labels are drawn on the chart so values can be read without hovering.
"""

from __future__ import annotations

import altair as alt
import pandas as pd

from .config import BLUE, GRID, INK, INK_SECONDARY, SERIES, SURFACE

TOKENS_MEASURE = "Tokens vs English"
BYTES_MEASURE = "Raw size (bytes) vs English"
ADDS = "Costlier than bytes"
SAVES = "Cheaper than bytes"


def _title(text: str, subtitle: str | None = None) -> alt.TitleParams:
    return alt.TitleParams(
        text=text,
        subtitle=[subtitle] if subtitle else [],
        anchor="start",
        color=INK,
        subtitleColor=INK_SECONDARY,
        fontSize=15,
        subtitleFontSize=12,
        fontWeight="bold",
        offset=8,
    )


def _finish(chart: alt.TopLevelMixin, height: int) -> alt.TopLevelMixin:
    return (
        chart.properties(height=height, width="container", background=SURFACE, padding={"left": 6, "right": 16, "top": 6, "bottom": 6})
        .configure_view(strokeWidth=0)
        .configure_axis(
            labelColor=INK_SECONDARY,
            titleColor=INK,
            labelFontSize=12,
            titleFontSize=12,
            titleFontWeight="normal",
            gridColor=GRID,
            domainColor=GRID,
            tickColor=GRID,
        )
        .configure_legend(labelColor=INK, titleColor=INK, labelFontSize=12, titleFontSize=12, symbolSize=110)
    )


def _times(values: pd.Series, digits: int = 2) -> pd.Series:
    return values.map(lambda v: f"{v:.{digits}f}×")


# ------------------------------------------------------------------ story 1


def premium_bar(frame: pd.DataFrame, tokenizer: str) -> alt.TopLevelMixin:
    """Ranking: premium by language for one tokeniser, English = 1.0 reference.

    Form: horizontal sorted bars, because the task is to rank 15 named
    categories on one magnitude. Rejected: a column chart (language names would
    need rotating) and a heatmap (cannot be read to two decimals). The black
    tick is the UTF-8 byte premium: what the language would cost if a token
    were a byte, so bar beyond tick = cost added by the tokeniser.
    """
    order = frame.sort_values("premium_vs_en", ascending=False)["language"].tolist()
    long = pd.concat(
        [
            frame.assign(measure=TOKENS_MEASURE, value=frame["premium_vs_en"]),
            frame.assign(measure=BYTES_MEASURE, value=frame["byte_premium_vs_en"]),
        ]
    )[["language", "measure", "value"]]
    long["label"] = _times(long["value"])
    peak = float(long["value"].max())
    long["label_x"] = peak * 1.06  # labels sit in one column so they never collide with ticks

    y = alt.Y("language:N", sort=order, title=None, axis=alt.Axis(labelLimit=220, labelColor=INK, labelFontSize=12))
    x = alt.X(
        "value:Q",
        title="Premium vs English (× English = 1.0)",
        scale=alt.Scale(domain=[0, peak * 1.3], nice=False),
    )
    color = alt.Color(
        "measure:N",
        scale=alt.Scale(domain=[TOKENS_MEASURE, BYTES_MEASURE], range=[BLUE, INK]),
        legend=alt.Legend(title=None, orient="top", symbolType="square"),
    )
    base = alt.Chart(long)
    bars = (
        base.transform_filter(alt.datum.measure == TOKENS_MEASURE)
        .mark_bar(cornerRadiusEnd=4, size=15)
        .encode(x=x, y=y, color=color)
    )
    ticks = (
        base.transform_filter(alt.datum.measure == BYTES_MEASURE)
        .mark_tick(thickness=3, size=22)
        .encode(x=x, y=y, color=color)
    )
    labels = (
        base.transform_filter(alt.datum.measure == TOKENS_MEASURE)
        .mark_text(align="left", color=INK, fontSize=12, fontWeight="bold")
        .encode(x=alt.X("label_x:Q", scale=alt.Scale(domain=[0, peak * 1.3], nice=False)), y=y, text="label:N")
    )
    one = alt.Chart(pd.DataFrame({"x": [1.0]})).mark_rule(strokeDash=[4, 3], color=INK_SECONDARY).encode(x="x:Q")
    chart = alt.layer(bars, ticks, labels, one).properties(
        title=_title(f"Cost vs English by language: {tokenizer}", "Bars: tokens needed ÷ English tokens. Black tick: raw size in bytes ÷ English bytes.")
    )
    return _finish(chart, 24 * len(order) + 70)


def byte_gap_bar(frame: pd.DataFrame, tokenizer: str) -> alt.TopLevelMixin:
    """Deviation: token premium ÷ byte premium, drawn from the 1.0 baseline.

    Form: diverging bars around 1.0 on a log axis, because the task is to see
    which languages pay more (or less) than their raw UTF-8 encoding would
    suggest, and by how much. Bars right of 1.0: the tokeniser adds cost beyond
    encoding. Rejected: a scatter of token premium against byte premium, whose
    15 labels collide in the dense 1 to 2 region and cannot all be read.
    """
    data = frame.copy()
    data["base"] = 1.0
    data["direction"] = data["premium_over_byte"].ge(1.0).map({True: ADDS, False: SAVES})
    data["label"] = _times(data["premium_over_byte"])
    order = data.sort_values("premium_over_byte", ascending=False)["language"].tolist()
    lo = min(0.4, float(data["premium_over_byte"].min()) * 0.75)
    hi = max(2.0, float(data["premium_over_byte"].max()) * 1.45)
    scale = alt.Scale(type="log", domain=[lo, hi], nice=False)
    y = alt.Y("language:N", sort=order, title=None, axis=alt.Axis(labelLimit=220, labelColor=INK, labelFontSize=12))
    x = alt.X(
        "premium_over_byte:Q",
        title="Token premium ÷ byte premium (log scale; 1.0 = the tokeniser adds nothing)",
        scale=scale,
        axis=alt.Axis(values=[0.5, 1, 2, 4], format="~g"),
    )
    color = alt.Color(
        "direction:N",
        scale=alt.Scale(domain=[ADDS, SAVES], range=[SERIES[1], SERIES[0]]),
        legend=alt.Legend(title=None, orient="top", symbolType="square"),
    )
    bars = alt.Chart(data).mark_bar(size=15).encode(x=x, x2="base:Q", y=y, color=color)
    right = (
        alt.Chart(data[data["premium_over_byte"] >= 1.0])
        .mark_text(align="left", dx=6, fontSize=12, color=INK, fontWeight="bold")
        .encode(x=alt.X("premium_over_byte:Q", scale=scale), y=y, text="label:N")
    )
    left = (
        alt.Chart(data[data["premium_over_byte"] < 1.0])
        .mark_text(align="right", dx=-6, fontSize=12, color=INK, fontWeight="bold")
        .encode(x=alt.X("premium_over_byte:Q", scale=scale), y=y, text="label:N")
    )
    one = alt.Chart(pd.DataFrame({"x": [1.0]})).mark_rule(color=INK_SECONDARY).encode(x=alt.X("x:Q", scale=scale))
    chart = alt.layer(bars, right, left, one).properties(
        title=_title(f"Can script alone explain the token gap? {tokenizer}", "Token premium ÷ byte premium. Above 1.0 the tokeniser charges more than the text's raw size explains.")
    )
    return _finish(chart, 24 * len(order) + 70)


# ------------------------------------------------------------------ story 3: safety margin


def buffer_band(buffers: pd.DataFrame, tokenizer: str, coverage: float) -> alt.TopLevelMixin:
    """Distribution: spread of the per-sentence premium inside each language.

    Form: thin line (middle 90% of sentences), thick bar (middle half), dot
    (aggregate premium) and a black tick (premium that covers `coverage` of
    sentences), sorted by median. The task is to compare the spread of 200
    values across 14 languages: a strip plot of 2,800 dots overprints, and a
    box plot hides the covering tick that the decision needs.
    """
    data = buffers.copy()
    order = data.sort_values("p50", ascending=False)["language"].tolist()
    data["tick_label"] = data["covered"].map(lambda v: f"{v:.2f}×") + "  (+" + (data["buffer_pct"] * 100).round(0).astype(int).astype(str) + "%)"
    lo = max(0.8, float(data["p05"].min()) * 0.9)
    hi = float(data["covered"].max()) * 1.9
    scale = alt.Scale(type="log", domain=[lo, hi], nice=False)
    y = alt.Y("language:N", sort=order, title=None, axis=alt.Axis(labelLimit=220, labelColor=INK, labelFontSize=12))
    axis = alt.Axis(values=[1, 2, 4, 8], format="~g")
    x_title = "Premium vs English per sentence (× tokens, log scale)"
    line = alt.Chart(data).mark_rule(strokeWidth=2, color=BLUE, opacity=0.55).encode(x=alt.X("p05:Q", scale=scale, title=x_title, axis=axis), x2="p75:Q", y=y)
    line_hi = alt.Chart(data).mark_rule(strokeWidth=2, color=BLUE, opacity=0.55).encode(x=alt.X("p75:Q", scale=scale), x2="covered:Q", y=y)
    iqr = alt.Chart(data).mark_bar(size=9, color=BLUE, opacity=0.9, cornerRadius=2).encode(x=alt.X("p25:Q", scale=scale), x2="p75:Q", y=y)
    avg = alt.Chart(data).mark_circle(size=70, color=SURFACE, stroke=INK, strokeWidth=1.5, opacity=1).encode(x=alt.X("average:Q", scale=scale), y=y)
    tick = alt.Chart(data).mark_tick(thickness=3, size=20, color=INK).encode(x=alt.X("covered:Q", scale=scale), y=y)
    text = alt.Chart(data).mark_text(align="left", dx=8, fontSize=11, color=INK, fontWeight="bold").encode(
        x=alt.X("covered:Q", scale=scale), y=y, text="tick_label:N"
    )
    chart = alt.layer(line, line_hi, iqr, avg, tick, text).properties(
        title=_title(
            f"How much buffer does each language need? {tokenizer}",
            f"Blue bar: middle half of sentences. Circle: average. Black tick: fits {coverage:.0%} of sentences.",
        )
    )
    return _finish(chart, 24 * len(order) + 70)


def sentence_histogram(sentences: pd.DataFrame, language: str, average: float, covered: float, coverage: float) -> alt.TopLevelMixin:
    """Distribution: the 200 per-sentence premiums behind one row of the band chart.

    Form: histogram, because the task is to see the shape (skew, outliers)
    that the percentiles summarise. Rejected: a density curve, which implies
    smoothness that 200 points cannot support.
    """
    rules = pd.DataFrame(
        {"x": [average, covered], "label": [f"Average {average:.2f}×", f"Covers {coverage:.0%}: {covered:.2f}×"], "dash": ["solid", "dashed"]}
    )
    bars = alt.Chart(sentences).mark_bar(color=BLUE, stroke=SURFACE, strokeWidth=1).encode(
        x=alt.X("premium:Q", bin=alt.Bin(maxbins=24), title="Premium vs English for one sentence (× tokens)"),
        y=alt.Y("count():Q", title="Sentences"),
    )
    lines = alt.Chart(rules).mark_rule(color=INK, strokeWidth=2).encode(
        x="x:Q", strokeDash=alt.StrokeDash("dash:N", legend=None, scale=alt.Scale(domain=["solid", "dashed"], range=[[1, 0], [5, 4]]))
    )
    text = alt.Chart(rules).mark_text(align="left", dx=6, dy=-4, baseline="bottom", fontSize=11, color=INK, fontWeight="bold").encode(
        x="x:Q", y=alt.value(0), text="label:N"
    )
    chart = alt.layer(bars, lines, text).properties(title=_title(f"The 200 sentences behind it: {language}", "Each bar counts sentences with that premium."))
    return _finish(chart, 24 * 8 + 70)


# ------------------------------------------------------------------ story 4: pricing tiers

TIER_NAMES = {1: "Tier 1", 2: "Tier 2", 3: "Tier 3"}


def tier_dumbbell(rows: pd.DataFrame, tokenizer: str, bounds: tuple[float, float]) -> alt.TopLevelMixin:
    """Comparison: each language's real cost against the price its tier charges.

    Form: dumbbell (dot = real premium, tick = tier price, line = overcharge)
    sorted by premium, because the task is to see how far a tier price sits
    above what each language really costs. Rejected: a table (the gap is the
    message) and bars for both values (two bars per language double the ink for one gap).
    """
    data = rows.copy()
    data["tier_name"] = data["tier"].map(TIER_NAMES)
    data["row"] = data["language"] + " · " + data["script"]
    data["gap_label"] = "+" + (data["over_tier"] * 100).round(0).astype(int).astype(str) + "%"
    order = data.sort_values("premium_vs_en", ascending=False)["row"].tolist()
    peak = float(data["tier_price"].max())
    scale = alt.Scale(type="log", domain=[0.85, peak * 1.9], nice=False)
    y = alt.Y("row:N", sort=order, title=None, axis=alt.Axis(labelLimit=260, labelColor=INK, labelFontSize=12))
    tier_scale = alt.Scale(domain=list(TIER_NAMES.values()), range=[SERIES[0], SERIES[1], SERIES[2]])
    color = alt.Color("tier_name:N", scale=tier_scale, legend=alt.Legend(title=None, orient="top", symbolType="circle"))
    axis = alt.Axis(values=[1, 2, 4, 8, 16], format="~g")
    link = alt.Chart(data).mark_rule(strokeWidth=3, opacity=0.5).encode(
        x=alt.X("premium_vs_en:Q", scale=scale, title="Premium vs English (× tokens, log scale)", axis=axis), x2="tier_price:Q", y=y, color=color
    )
    dot = alt.Chart(data).mark_circle(size=100, opacity=1, stroke=SURFACE, strokeWidth=2).encode(x=alt.X("premium_vs_en:Q", scale=scale), y=y, color=color)
    tick = alt.Chart(data).mark_tick(thickness=3, size=18, color=INK).encode(x=alt.X("tier_price:Q", scale=scale), y=y)
    text = alt.Chart(data).mark_text(align="left", dx=9, fontSize=11, color=INK, fontWeight="bold").encode(
        x=alt.X("tier_price:Q", scale=scale), y=y, text="gap_label:N"
    )
    low, high = 0.85, peak * 1.9
    edges = [low, min(max(bounds[0], low), high), min(max(bounds[1], low), high), high]
    bands = pd.DataFrame(
        {
            "tier_name": list(TIER_NAMES.values()),
            "start": edges[:3],
            "end": edges[1:],
        }
    )
    band = alt.Chart(bands).mark_rect(opacity=0.13).encode(
        x=alt.X("start:Q", scale=scale), x2="end:Q", color=alt.Color("tier_name:N", scale=tier_scale, legend=None)
    )
    band_text = alt.Chart(bands).mark_text(align="left", dx=5, dy=10, fontSize=11, fontWeight="bold", color=INK_SECONDARY, clip=True).encode(
        x=alt.X("start:Q", scale=scale), y=alt.value(0), text="tier_name:N"
    )
    cut_line = alt.Chart(pd.DataFrame({"x": [bounds[0], bounds[1]]})).mark_rule(strokeDash=[5, 4], strokeWidth=1.5, color=INK_SECONDARY, clip=True).encode(
        x=alt.X("x:Q", scale=scale)
    )
    chart = alt.layer(band, cut_line, band_text, link, dot, tick, text).properties(
        title=_title(
            f"What each tier overcharges: {tokenizer}",
            "Shaded bands: the three tiers. Dot: real premium. Black tick: the tier's price (its costliest language). Label: overcharge.",
        )
    )
    return _finish(chart, 24 * len(order) + 70)


# ------------------------------------------------------------------ story 2: is the gap shrinking

def trend_chart(rows: pd.DataFrame, measure: str, measure_label: str, log: bool) -> alt.TopLevelMixin:
    """Change over time: one row per tokeniser family, one dot per version, oldest to newest.

    Form: a slope-style dot line per family (all rows share one axis), because the
    task is to see, for each family, whether its newer version sits left of its older
    one. Rejected: a line chart over release date (only 12 points, 9 dates unverified,
    and several families have a single version) and grouped bars (the direction of
    change between versions would have to be compared across bars). Colour follows the
    family (fixed slot), version names are written next to their dot, alternating
    above and below so neighbouring names cannot collide.
    """
    from .config import FAMILY_ORDER

    data = rows.copy()
    data["value"] = data[measure]
    data["label"] = data["tokenizer"] + " · " + data["value"].map(lambda v: f"{v:.2f}")
    # Alternate above/below within a family so labels of neighbouring versions do not overlap.
    families = [f for f in FAMILY_ORDER if f in set(data["family"])]
    labels = [data.loc[data["family"] == f, "family_label"].iloc[0] for f in families]
    colours = [SERIES[FAMILY_ORDER.index(f)] for f in families]
    low, high = float(data["value"].min()), float(data["value"].max())
    if log:
        scale = alt.Scale(type="log", domain=[low / 1.35, high * 1.5], nice=False)
        axis = alt.Axis(values=[v for v in (1, 1.5, 2, 3, 4, 6, 8, 12, 16) if low / 1.35 <= v <= high * 1.5], format="~g")
    else:
        scale = alt.Scale(domain=[0, max(high * 1.18, 0.1)], nice=False)
        axis = alt.Axis(format=".2f", tickCount=6)
    y = alt.Y("family_label:N", sort=labels, title=None, axis=alt.Axis(labelLimit=160, labelColor=INK, labelFontSize=13, labelPadding=8))
    color = alt.Color("family_label:N", scale=alt.Scale(domain=labels, range=colours), legend=None)
    x = alt.X("value:Q", scale=scale, title=measure_label + (" (log scale)" if log else ""), axis=axis)
    line = alt.Chart(data).mark_line(strokeWidth=3, opacity=0.55).encode(x=x, y=y, color=color, detail="family:N", order=alt.Order("generation_order:Q"))
    dots = alt.Chart(data).mark_circle(size=170, opacity=1, stroke=SURFACE, strokeWidth=2).encode(
        x=x, y=y, color=color,
        tooltip=[
            alt.Tooltip("tokenizer:N", title="Tokeniser"),
            alt.Tooltip("value:Q", title=measure_label, format=".3f"),
            alt.Tooltip("costliest_language:N", title="Costliest language"),
            alt.Tooltip("release_date:T", title="Release date", format="%b %Y"),
        ],
    )
    above = alt.Chart(data).transform_filter(alt.datum.generation_order % 2 == 1).mark_text(align="center", dy=-15, fontSize=11, color=INK).encode(x=x, y=y, text="label:N")
    below = alt.Chart(data).transform_filter(alt.datum.generation_order % 2 == 0).mark_text(align="center", dy=17, fontSize=11, color=INK).encode(x=x, y=y, text="label:N")
    chart = alt.layer(line, dots, above, below).properties(
        title=_title(
            "Older to newer versions of each tokeniser family",
            "Each row is one family, each dot one version. A newer version to the left of an older one means a smaller gap.",
        )
    )
    return _finish(chart, 78 * len(families) + 80)
