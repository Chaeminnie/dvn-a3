"""Streamlit views. Each view is a container whose key matches its id in dashboard.yml.

Every view follows the same contract as the course starter: heading, unit,
latest observation, controls, a "Selected:" line, an empty-state message,
outputs (chart, metrics, download) and a source line, all inside the container.

Narrative: a pricing and monetisation lead has to decide how to price and set
quotas for non-English users. Story 1 shows whether the gap is shrinking (the
headline), story 2 that script alone does not explain it, and stories 3 and 4 what
it means for pricing: how much buffer a quota needs and whether three tiers beat one price.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

from . import charts, config, data
from .config import (
    BACKGROUND_PAPERS,
    CONTEXT,
    DEFAULT_TOKENIZER,
    ENGLISH,
    FLORES_RETRIEVED,
    GLOSSARY,
    LAST_REFRESH,
    PERSONA,
    QUESTION,
    SCRIPT_NAMES,
    TOKEN_COUNTS_RUN,
    TOKENIZER_LABELS,
)

EMPTY_MESSAGE = "No observations match the selected filters."
UNIT_PREMIUM = "Unit: premium (×) = tokens a language needs ÷ tokens English needs for the same sentences, on the same tokeniser (English = 1.0×)"
SOURCE_PREMIUM = (
    "Source: data/processed/token_premium.csv, built from FLORES+ devtest sentences "
    "(200-sentence sample, about ±3%) and 12 tokenisers."
)
SOURCE_PUBLISHED = (
    " Comparison values: data/reference/published_premiums.csv (Petrov et al., 2023, Tables 1 and 5)."
)
SOURCE_SENTENCES = (
    "Source: data/processed/token_counts_long.csv (tokens per sentence; the same FLORES+ sentence in every language) "
    "and token_premium.csv for the average."
)
COVERAGE_LABELS = {level: f"{level:.0%}" for level in data.COVERAGE_LEVELS}


# ------------------------------------------------------------------ cached data


@st.cache_data
def premium_table() -> pd.DataFrame:
    return data.load_premium()


@st.cache_data
def gini_table() -> pd.DataFrame:
    return data.load_gini()


@st.cache_data
def tokenizer_table() -> pd.DataFrame:
    return data.load_tokenizers()


@st.cache_data
def langs_table() -> pd.DataFrame:
    return data.load_langs()


@st.cache_data
def mix_table() -> pd.DataFrame:
    return data.load_mix()


# Cached results are pickled dataclasses. If data.py changes while a server is running, an old pickled
# instance would be missing the new fields (AttributeError), so the code version is part of the cache key.
CODE_VERSION = hashlib.md5(Path(data.__file__).read_bytes() + Path(config.__file__).read_bytes()).hexdigest()[:12]


@st.cache_data
def _facts(version: str) -> data.Facts:
    return data.compute_facts(premium_table(), gini_table(), tokenizer_table())


@st.cache_data
def _pricing_facts(version: str) -> data.PricingFacts:
    return data.compute_pricing_facts(premium_table(), counts_long(), mix_table(), DEFAULT_TOKENIZER)


@st.cache_data
def _buffer_range(version: str) -> data.BufferRange:
    return data.compute_buffer_range(premium_table(), counts_long())


def buffer_range() -> data.BufferRange:
    return _buffer_range(CODE_VERSION)


@st.cache_data
def _all_tokenisers(version: str) -> data.AllTokenisers:
    return data.compute_all_tokenisers(premium_table(), counts_long(), mix_table())


def all_tokenisers() -> data.AllTokenisers:
    return _all_tokenisers(CODE_VERSION)


def facts() -> data.Facts:
    return _facts(CODE_VERSION)


def pricing_facts() -> data.PricingFacts:
    return _pricing_facts(CODE_VERSION)


@st.cache_data
def counts_long() -> pd.DataFrame:
    return data.load_counts_long()


@st.cache_data
def sentences_for(tokenizer_id: str) -> pd.DataFrame:
    return data.sentence_premiums(counts_long(), tokenizer_id)


@st.cache_data
def flores_sample() -> pd.DataFrame:
    return data.load_flores_sample()


@st.cache_data
def sample_check() -> pd.DataFrame:
    return data.load_sample_check()


# ------------------------------------------------------------------ helpers


def times(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}×"


def pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def story_titles() -> dict[str, str]:
    """Section headings that state the finding across every tokeniser. Every number is computed, so each can be traced."""
    f = facts()
    b = buffer_range()
    a = all_tokenisers()
    cheapest = "all" if f.english_cheapest_on == f.n_tokenizers else f"{f.english_cheapest_on} of"
    tiers_scope = f"on all {a.n_tokenizers}" if a.tiers_beat_flat_on == a.n_tokenizers else f"on {a.tiers_beat_flat_on} of {a.n_tokenizers}"
    return {
        "premium_by_language": (
            f"English is the cheapest language on {cheapest} {f.n_tokenizers} tokenisers; other languages need "
            f"{f.min_premium:.2f}× to {f.max_premium:.2f}× as many tokens"
        ),
        "tokeniser_trend": (
            f"Newer tokenisers are usually fairer than older ones: {len(f.families_fairer)} of {f.families_multi} families improved across {f.n_tokenizers} tokenisers"
        ),
        "buffer_by_language": (
            f"On all {b.n_tokenizers} tokenisers, fitting {pct(b.coverage)} of sentences takes {pct(b.low)} to {pct(b.high)} "
            "more tokens than the average premium suggests"
        ),
        "pricing_tiers": (
            f"Three price tiers beat one price {tiers_scope} tokenisers: the average overcharge is {pct(a.over_tier_low)} to {pct(a.over_tier_high)}, "
            f"against {pct(a.over_flat_low)} to {pct(a.over_flat_high)} for one price"
        ),
    }


def not_shown(*points: str) -> None:
    with st.expander("What this does not show"):
        st.markdown("\n".join(f"- {point}" for point in points))


def how_to_use(*steps: str) -> None:
    """Plain instructions for the controls of one story, shown under its heading."""
    st.markdown("**How to use this section:** " + " ".join(steps))


TIER_COLOURS = {1: config.SERIES[0], 2: config.SERIES[1], 3: config.SERIES[2]}


def english_note(extra: str) -> None:
    """Why English is missing from a 14-language selector."""
    st.caption("English is not in this list. " + extra)


def tier_range_text(tier: int, bounds: tuple[float, float]) -> str:
    if tier == 1:
        return f"up to {bounds[0]:.1f}×"
    if tier == 2:
        return f"{bounds[0]:.1f}× to {bounds[1]:.1f}×"
    return f"above {bounds[1]:.1f}×"


def tier_cards(container, bounds: tuple[float, float], tiered: pd.DataFrame | None) -> None:
    """Three colour-coded cards, one per tier, that show the cut-offs and what each tier holds. One slider moves all three."""
    with container:
        cols = st.columns(3)
        for tier, col in zip((1, 2, 3), cols):
            members = tiered[tiered["tier"] == tier] if tiered is not None else None
            if members is None:
                detail = "&nbsp;"
            elif members.empty:
                detail = "No language in this range, so no price"
            else:
                detail = (
                    f"<b>{len(members)}</b> language{'s' if len(members) != 1 else ''} · price <b>{members['tier_price'].iloc[0]:.2f}×</b> · "
                    f"mean overcharge <b>{pct(members['over_tier'].mean())}</b>"
                )
            col.markdown(
                f"<div style='border:1px solid {config.GRID};border-top:6px solid {TIER_COLOURS[tier]};border-radius:6px;padding:10px 14px;background:{config.SURFACE};color:{config.INK}'>"
                f"<div style='font-size:0.85rem;color:{config.INK_SECONDARY}'>Tier {tier}</div>"
                f"<div style='font-size:1.6rem;font-weight:600;line-height:1.3'>{tier_range_text(tier, bounds)}</div>"
                f"<div style='font-size:0.85rem;margin-top:4px'>{detail}</div></div>",
                unsafe_allow_html=True,
            )
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)


def selected_line(names: list[str], total: int) -> str:
    if not names:
        return "Selected: none"
    if len(names) <= 4:
        return f"Selected: {', '.join(names)}"
    return f"Selected: {len(names)} of {total} languages"


def _step_tokenizer(key: str, step: int) -> None:
    """Button callback: move the tokeniser selection one place along the list."""
    ids = list(tokenizer_table()["tokenizer_id"])
    position = ids.index(st.session_state[key]) + step
    st.session_state[key] = ids[min(max(position, 0), len(ids) - 1)]


def tokenizer_select(key: str, label: str = "Tokeniser") -> str:
    """Tokeniser dropdown on its own row, with previous / next buttons so one click moves one tokeniser."""
    ids = list(tokenizer_table()["tokenizer_id"])
    st.session_state.setdefault(key, DEFAULT_TOKENIZER)
    box, previous, following, _ = st.columns([3, 1, 1, 4], vertical_alignment="bottom")
    chosen = box.selectbox(label, ids, format_func=lambda t: TOKENIZER_LABELS[t], key=key)
    position = ids.index(chosen)
    previous.button(
        "← Previous", key=f"{key}_previous", on_click=_step_tokenizer, args=(key, -1), disabled=position == 0, width="stretch",
        help="Show the previous tokeniser in the list",
    )
    following.button(
        "Next →", key=f"{key}_next", on_click=_step_tokenizer, args=(key, 1), disabled=position == len(ids) - 1, width="stretch",
        help="Show the next tokeniser in the list",
    )
    return chosen


def rows_for(tokenizer_id: str) -> pd.DataFrame:
    rows = premium_table()
    rows = rows[rows["tokenizer_id"] == tokenizer_id].copy()
    rows["script"] = rows["iso_15924"].map(SCRIPT_NAMES)
    return rows


# ------------------------------------------------------------------ opening


def render_opening() -> None:
    f = facts()
    p = pricing_facts()
    st.title("Do some languages cost more tokens than others when using AI models?")
    st.write(CONTEXT)
    st.write(f"**Question:** {QUESTION}")
    st.caption(f"Audience: {PERSONA} References are listed at the end of the page.")

    with st.container(key="overview"):
        cols = st.columns(3)
        cols[0].metric(
            "Tokenisers where English is cheapest",
            f"{f.english_cheapest_on} of {f.n_tokenizers}",
            help=f"Premium of every other language is at least {f.min_premium:.2f}× on every tokeniser.",
            border=True,
        )
        cols[1].metric(
            "Costliest language",
            f"{f.costliest_language} · {f.costliest_language_count} of {f.n_tokenizers}",
            help=f"{f.costliest_language} needs the most tokens of any language on {f.costliest_language_count} of {f.n_tokenizers} tokenisers "
            f"({times(f.costliest_low)} to {times(f.costliest_high)} English). On the other {f.n_tokenizers - f.costliest_language_count} "
            f"({f.costliest_elsewhere}) it is {f.other_costliest}.",
            border=True,
        )
        cols[2].metric(
            "Families where newer versions are fairer",
            f"{len(f.families_fairer)} of {f.families_multi}",
            help="Tokeniser families with more than one version whose newest version has a lower Gini (less unequal cost across languages) than the oldest.",
            border=True,
        )
        st.caption(
            f"Based on {f.n_languages} languages × {f.n_sentences} translated sentences (FLORES+) × {f.n_tokenizers} tokenisers. Later sections start on {p.tokenizer} because it runs locally "
            "through tiktoken, so anyone can re-run the counts (the Claude and Gemini counts come from the providers' token-counting services, which we cannot inspect). "
            "Premium = tokens a language needs ÷ tokens English needs for the same sentences (English = 1.0×)."
        )

        st.subheader("Implications for Pricing Strategies")
        st.markdown(answer_text(f, all_tokenisers(), buffer_range()))
        with st.expander("Glossary"):
            st.markdown(GLOSSARY)
        with st.expander("Limitations"):
            st.markdown(limits_text(f))


def answer_text(f: data.Facts, a: data.AllTokenisers, b: data.BufferRange) -> str:
    return (
        f"**Tokeniser design matters more than script.** The same language can be cheap on one tokeniser and expensive on another. {f.swing_language}, for example, ranges from "
        f"{times(f.swing_low)} to {times(f.swing_high)} the English token count depending on the tokeniser. Newer tokenisers are usually more equitable than earlier versions, suggesting that "
        f"much of the language gap reflects design choices rather than unavoidable features of writing systems. However, even the fairest tokeniser still assigns {f.fairest_max_language} "
        f"{times(f.fairest_max_premium)} as many tokens as English.\n\n"
        f"**For pricing, use tiers and quota buffers.** Since token costs still differ substantially across languages, a single global pricing rule tends to overcharge many users. "
        f"A tiered pricing system could mitigate this problem, and quota allowances should include an additional {pct(b.low)} to {pct(b.high)} buffer because token costs vary "
        "considerably even within the same language."
    )


def limits_text(f: data.Facts) -> str:
    tokenisers = tokenizer_table()
    unverified = int((tokenisers["date_basis"] != "official").sum())
    return (
        f"- A limited sample: {f.n_languages} team-selected languages and {f.n_sentences} translated sentences per language, not real prompts. Longer texts smooth out some variation, so the buffers are an upper limit.\n"
        f"- Token cost only: input tokens, with no output tokens, list prices, latency or answer quality.\n"
        f"- Tier calculations assume equal usage across languages (placeholder) and price each tier at its costliest language.\n"
        f"- Script and training data cannot be separated, so the effect of the writing system, language structure and tokeniser training data cannot be isolated.\n"
        f"- Several tokenisers are black-box APIs, and {unverified} of {len(tokenisers)} tokeniser release dates are unverified."
    )


# ------------------------------------------------------------------ story 2: script alone


def published_comparison() -> str:
    """One or two sentences comparing our cl100k premiums with the values Petrov et al. (2023) published for the same languages."""
    table = data.compare_published(premium_table())
    worst = table["gap_pct"].abs().max()
    tokens = table[table["measure"] == "tokens"]
    example = tokens.loc[tokens["published_value"].idxmax()]
    return (
        f"Our numbers also match published ones: for the {len(table)} values that Petrov et al. (2023) report for the same languages "
        f"(the cl100k tokeniser and bytes), ours are within {worst * 100:.1f}%, for example {example['language']} at {times(example['ours'])} against {times(example['published_value'])} published."
    )


def render_premium_view() -> None:
    premium = premium_table()
    langs = langs_table()
    name_to_code = dict(zip(langs["language"], langs["lang_code"]))
    all_names = sorted(langs["language"])

    with st.container(key="premium_by_language"):
        st.header(story_titles()["premium_by_language"])
        st.caption(UNIT_PREMIUM)
        st.caption(f"Latest observation: {TOKEN_COUNTS_RUN}")
        how_to_use(
            "Click **← Previous** or **Next →** to step through the 12 tokenisers one at a time, or open the dropdown to jump to one.",
            "In **Languages**, click the × on a language to remove it from the charts, click the box to add it back, or use the × at the far right to clear all.",
            "Open **Table view** for the exact values, **Trace a number back to its source files** to see how one premium is built, and **Download filtered data** to save what is shown.",
        )

        tokenizer_id = tokenizer_select("tokenizer_filter")
        chosen = st.multiselect("Languages", all_names, default=all_names, key="language_filter")
        st.write(selected_line(chosen, len(all_names)))

        frame = premium[(premium["tokenizer_id"] == tokenizer_id) & (premium["language"].isin(chosen))]
        label = TOKENIZER_LABELS[tokenizer_id]
        if frame.empty:
            st.info(EMPTY_MESSAGE)
        else:
            non_en = frame[frame["lang_code"] != ENGLISH]
            m = st.columns(2)
            if non_en.empty:
                m[0].metric("Costliest selected language", "n/a (English only)")
            else:
                top = non_en.loc[non_en["premium_vs_en"].idxmax()]
                m[0].metric("Costliest selected language", f"{top['language']} · {times(top['premium_vs_en'])}")
            m[1].metric("Median premium, selected", times(frame["premium_vs_en"].median()))

            left, right = st.columns(2)
            with left:
                st.altair_chart(charts.premium_bar(frame, label), width="stretch", theme=None)
            with right:
                st.altair_chart(charts.byte_gap_bar(frame, label), width="stretch", theme=None)
            st.caption(
                "How to read the charts: on the left, each bar is how many times more tokens the language needs than English. The black tick is how many times more "
                "storage space (bytes) its text takes. A bar longer than its tick means the tokeniser adds cost on top of what the way the language is written explains. "
                "The right chart shows that extra cost directly (token premium ÷ byte premium; 1.0 means none). "
                "Chart types (FT Visual Vocabulary): left, Ranking (ordered bar); right, Deviation (diverging bar)."
            )
            if not non_en.empty:
                top_row = non_en.loc[non_en["premium_vs_en"].idxmax()]
                above = int((non_en["premium_over_byte"] > 1).sum())
                st.markdown(
                    f"**Takeaway:** On {label}, {top_row['language']} needs {times(top_row['premium_vs_en'])} the tokens of English. "
                    + (
                        f"{above} of {len(non_en)} selected languages cost more than their raw size in bytes alone explains, so the tokeniser, not only the script, adds to the gap."
                        if above
                        else "No selected language costs more than its raw size in bytes explains, so script alone accounts for the gap on this tokeniser."
                    )
                )
                st.caption(published_comparison())
            not_shown(
                "Translated FLORES+ sentences, not real prompts. Cost only: answer quality is not measured, and more tokens per word goes with lower accuracy on an African-language benchmark (Lundin et al., 2026).",
                "Each premium rests on 200 sentences per language (about ±3%), so the full FLORES-200 text would give slightly different values.",
                "Script and language are not separated: how many bytes and spaces a language needs explains part of the premium (Arnett et al., 2025), and we have no training data per language.",
            )

        with st.expander("Table view of the values in these charts"):
            table = frame[["language", "premium_vs_en", "byte_premium_vs_en", "premium_over_byte", "mean_tokens_per_sentence"]].sort_values(
                "premium_vs_en", ascending=False
            )
            st.dataframe(
                table,
                hide_index=True,
                width="stretch",
                column_config={
                    "language": "Language",
                    "premium_vs_en": st.column_config.NumberColumn("Token premium (× English)", format="%.2f"),
                    "byte_premium_vs_en": st.column_config.NumberColumn("Byte premium (× English)", format="%.2f"),
                    "premium_over_byte": st.column_config.NumberColumn("Token ÷ byte premium", format="%.2f"),
                    "mean_tokens_per_sentence": st.column_config.NumberColumn("Mean tokens per sentence", format="%.1f"),
                },
            )

        render_trace(tokenizer_id, name_to_code)

        st.caption(SOURCE_PREMIUM + SOURCE_PUBLISHED)
        st.download_button(
            "Download filtered data",
            data=frame.drop(columns=["family_label", "release_date"]).to_csv(index=False).encode("utf-8"),
            file_name="premium_by_language_filtered.csv",
            mime="text/csv",
            key="premium_download",
        )


def render_trace(tokenizer_id: str, name_to_code: dict[str, str]) -> None:
    """Trace one displayed premium back through token_premium.csv to the sentences."""
    with st.expander("Trace a number back to its source files"):
        names = sorted(name_to_code)
        default = names.index("Burmese") if "Burmese" in names else 0
        language = st.selectbox("Language to trace", names, index=default, key="trace_language")
        code = name_to_code[language]
        premium = premium_table()
        row = premium[(premium["lang_code"] == code) & (premium["tokenizer_id"] == tokenizer_id)].iloc[0]
        english = premium[(premium["lang_code"] == ENGLISH) & (premium["tokenizer_id"] == tokenizer_id)].iloc[0]
        counts = counts_long()
        counts = counts[counts["tokenizer_id"] == tokenizer_id]
        lang_total = int(counts.loc[counts["lang_code"] == code, "n_tokens"].sum())
        en_total = int(counts.loc[counts["lang_code"] == ENGLISH, "n_tokens"].sum())
        st.markdown(
            f"**{language} on {TOKENIZER_LABELS[tokenizer_id]}:** premium shown = total tokens {lang_total:,} ÷ English total tokens "
            f"{en_total:,} = **{times(lang_total / en_total, 4)}**.\n\n"
            f"- `token_premium.csv` stores `total_tokens` = {int(row['total_tokens']):,} and {int(english['total_tokens']):,} "
            f"(English) and `premium_vs_en` = {row['premium_vs_en']:.4f}.\n"
            f"- Re-adding `n_tokens` in `token_counts_long.csv` over {int(row['n_sentences'])} sentences gives the same totals: "
            f"{'match' if (lang_total, en_total) == (int(row['total_tokens']), int(english['total_tokens'])) else 'MISMATCH'}.\n"
            f"- Sentences come from `flores_sample.csv` (same `sent_id` in every language)."
        )
        sample = flores_sample()
        ids = sorted(sample.loc[sample["lang_code"] == ENGLISH, "sent_id"])[:4]
        rows = []
        for sent_id in ids:
            en_text = sample[(sample["lang_code"] == ENGLISH) & (sample["sent_id"] == sent_id)]["text"].iloc[0]
            lang_text = sample[(sample["lang_code"] == code) & (sample["sent_id"] == sent_id)]["text"].iloc[0]
            n_en = int(counts[(counts["lang_code"] == ENGLISH) & (counts["sent_id"] == sent_id)]["n_tokens"].iloc[0])
            n_lang = int(counts[(counts["lang_code"] == code) & (counts["sent_id"] == sent_id)]["n_tokens"].iloc[0])
            rows.append(
                {
                    "sent_id": sent_id,
                    "English (first 70 characters)": en_text[:70],
                    "English tokens": n_en,
                    f"{language} (first 40 characters)": lang_text[:40],
                    f"{language} tokens": n_lang,
                }
            )
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


# ------------------------------------------------------------------ story 1: is the gap shrinking (headline)


TREND_SCOPES = {"versions": "Families with more than one version", "all": "All families"}
TREND_LOG = {"gini": False, "max_premium": True, "median_premium": True}
TREND_METRIC_NOTE = {
    "gini": "Gini: 0 = every language costs the same; higher = more unequal.",
    "max_premium": "Tokens the costliest language needs ÷ tokens English needs.",
    "median_premium": "Tokens the middle language needs ÷ tokens English needs.",
}


TREND_PHRASE = {
    "gini": "the inequality of cost across languages (Gini)",
    "max_premium": "the costliest language's premium",
    "median_premium": "the median language's premium",
}


def trend_sentence(changes: pd.DataFrame, measure: str) -> str:
    """The takeaway statistic for one measure: how many families improved, the biggest improvement, and any family that did not move."""
    better = changes[changes["change"] < -1e-4]
    flat = changes[changes["change"].abs() <= 1e-4]
    worse = changes[changes["change"] > 1e-4]
    text = f"On {TREND_PHRASE[measure]}, newer versions improved in {len(better)} of {len(changes)} families"
    if len(better):
        top = better.iloc[0]
        text += f", most in {top['family_label']} ({abs(top['change']) * 100:.0f}% lower from {top['first']} to {top['last']})"
    text += ". "
    if len(flat):
        text += f"{' and '.join(flat['family_label'])} did not change. "
    if len(worse):
        text += f"{' and '.join(worse['family_label'])} got worse. "
    return text


def render_trend_view() -> None:
    gini = gini_table()
    tokenisers = tokenizer_table()
    trend = data.trend_table(gini, tokenisers)
    f = facts()

    with st.container(key="tokeniser_trend"):
        st.header(story_titles()["tokeniser_trend"])
        st.caption(
            "Unit: Gini (0 to 1) = how unequal the premiums of the 15 languages are; premium (×) = tokens a language needs ÷ tokens English needs for the same sentences (English = 1.0×)"
        )
        st.caption(f"Latest observation: {TOKEN_COUNTS_RUN}")
        how_to_use(
            "Choose a **Measure** to change what the dots show: how unequal languages are, how much the costliest language pays, or how much the middle language pays.",
            "Choose **Families** to show only the families with more than one version (where a change can be seen) or all of them.",
            "Hover over a dot for the release date and costliest language, or open **Table view** for the exact values.",
        )

        c1, c2 = st.columns(2)
        measure = c1.radio(
            "Measure", list(data.TREND_MEASURES), format_func=data.TREND_MEASURES.get, key="trend_measure",
            help="All three come from the same token counts. Gini needs every language; the other two follow one language each.",
        )
        scope = c2.radio("Families", list(TREND_SCOPES), format_func=TREND_SCOPES.get, key="trend_scope")
        shown = trend if scope == "all" else trend[trend["n_versions"] > 1]
        measure_label = data.TREND_MEASURES[measure]
        st.write(f"Selected: {measure_label}; {shown['family'].nunique()} families, {len(shown)} tokenisers")

        if shown.empty:
            st.info(EMPTY_MESSAGE)
        else:
            changes = data.family_changes(trend, measure)
            better = changes[changes["change"] < -1e-4]
            m = st.columns(3)
            m[0].metric("Families that improved", f"{len(better)} of {len(changes)}", help="Families with more than one tokeniser version whose newest version scores lower (fairer) than their oldest on the chosen measure.", border=True)
            top = changes.iloc[0]
            m[1].metric("Biggest improvement", f"{top['family_label']} · −{abs(top['change']) * 100:.0f}%", help=f"{top['first']} → {top['last']}: {top['first_value']:.2f} → {top['last_value']:.2f}.", border=True)
            gap = trend.loc[trend[measure].idxmin()]
            m[2].metric("Fairest tokeniser on this measure", f"{gap['tokenizer']} · {gap[measure]:.2f}", help=TREND_METRIC_NOTE[measure], border=True)

            st.altair_chart(charts.trend_chart(shown, measure, measure_label, TREND_LOG[measure]), width="stretch", theme=None)
            st.caption(
                "How to read the chart: each row is a tokeniser family and each dot one version, joined from oldest to newest. "
                "A newer version to the left of an older one means the gap got smaller. " + TREND_METRIC_NOTE[measure] + " "
                "Chart type (FT Visual Vocabulary): Change over time (slope-style dot line)."
            )
            st.markdown(
                f"**Takeaway:** {trend_sentence(changes, measure)}"
                f"The results suggest that most of the gap reflects tokeniser design rather than script alone. The gap is shrinking, but it has not closed: the fairest tokeniser ({f.fairest_tokenizer}) still needs {times(f.fairest_max_premium)} the tokens for {f.fairest_max_language}."
            )
            unverified = int((tokenisers["date_basis"] != "official").sum())
            not_shown(
                "Only a few versions: four families have more than one version and none has more than three, so each line is a comparison between versions, not a measured rate of change.",
                "Claude Haiku 4.5 and Claude Sonnet 5.5 are different model lines, not one model over time, so that family's change may reflect the model rather than an upgrade of the tokeniser.",
                f"Order is by version, not by date: {unverified} of {len(tokenisers)} release dates are unverified, so we cannot say how many months a change took.",
                "We do not know why a newer tokeniser is fairer (for example a larger vocabulary or more multilingual training text), only that its counts are lower.",
            )

        with st.expander("Table view of the values in this chart"):
            table = shown[["family_label", "tokenizer", "generation_order", "release_date", "gini", "max_premium", "costliest_language", "median_premium"]]
            st.dataframe(
                table,
                hide_index=True,
                width="stretch",
                column_config={
                    "family_label": "Family",
                    "tokenizer": "Tokeniser",
                    "generation_order": st.column_config.NumberColumn("Version order", format="%d"),
                    "release_date": st.column_config.DateColumn("Release date", format="YYYY-MM-DD"),
                    "gini": st.column_config.NumberColumn("Gini", format="%.3f"),
                    "max_premium": st.column_config.NumberColumn("Costliest language (×)", format="%.2f"),
                    "costliest_language": "Costliest language",
                    "median_premium": st.column_config.NumberColumn("Median language (×)", format="%.2f"),
                },
            )
            st.download_button(
                "Download filtered data",
                data=table.to_csv(index=False).encode("utf-8"),
                file_name="tokeniser_trend_filtered.csv",
                mime="text/csv",
                key="trend_download",
            )
        st.caption(
            "Source: data/processed/tokenizer_gini.csv (Gini and premiums across the 15 languages, one row per tokeniser) joined to data/source/tokenizers.csv "
            "(family, version order, release date)."
        )


# ------------------------------------------------------------------ story 3: safety margin


def render_buffer_view() -> None:
    langs = langs_table()
    non_en = sorted(langs.loc[langs["lang_code"] != ENGLISH, "language"])
    name_to_code = dict(zip(langs["language"], langs["lang_code"]))

    with st.container(key="buffer_by_language"):
        st.header(story_titles()["buffer_by_language"])
        st.caption("Unit: premium per sentence (×) = tokens of a sentence in a language ÷ tokens of the same sentence in English; buffer (%) = extra tokens needed on top of the average premium")
        st.caption(f"Latest observation: {TOKEN_COUNTS_RUN}")
        how_to_use(
            "Pick a tokeniser with **← Previous** / **Next →**, then choose how many sentences the quota should fit: **80%**, **90%** or **95%**.",
            "The black ticks, buffer figures and takeaway update. Remove languages from **Languages** to focus on a few.",
            "Use **Language to inspect** to see the 200 sentences behind one language's row on the left chart.",
        )

        tokenizer_id = tokenizer_select("buffer_tokenizer")
        coverage = st.radio(
            "Share of sentences the quota should fit",
            list(data.COVERAGE_LEVELS),
            index=list(data.COVERAGE_LEVELS).index(data.DEFAULT_COVERAGE),
            format_func=lambda v: f"{COVERAGE_LABELS[v]} of sentences",
            horizontal=True,
            key="coverage_level",
            help="How many of every 100 sentences the quota should cover. 95% means 95 of 100 sentences fit within the quota and 5 run over. "
            "A higher share means fewer users run out of tokens, but needs a larger buffer. This changes the black ticks, the buffer figures, the histogram line and the takeaway.",
        )
        chosen = st.multiselect("Languages", non_en, default=non_en, key="buffer_language_filter")
        english_note("Each sentence premium is measured against the same sentence in English, so English is always exactly 1.0× and has no spread to buffer.")
        st.write(selected_line(chosen, len(non_en)))

        label = TOKENIZER_LABELS[tokenizer_id]
        if not chosen:
            st.info(EMPTY_MESSAGE)
        else:
            sentences = sentences_for(tokenizer_id)
            buffers = data.buffer_table(sentences, rows_for(tokenizer_id), coverage)
            buffers = buffers[buffers["language"].isin(chosen)]
            lo = buffers.loc[buffers["buffer_pct"].idxmin()]
            hi = buffers.loc[buffers["buffer_pct"].idxmax()]
            joined = sentences.merge(buffers[["lang_code", "average"]], on="lang_code")
            share_fit = float((joined["premium"] <= joined["average"]).mean())
            m = st.columns(3)
            m[0].metric("Smallest buffer", f"{lo['language']} · +{pct(lo['buffer_pct'])}", help="The premium that fits the chosen share of sentences, divided by the average premium, minus 1.")
            m[1].metric("Largest buffer", f"{hi['language']} · +{pct(hi['buffer_pct'])}")
            m[2].metric("Sentences over a quota set at the average", pct(1 - share_fit), help="Share of sentences that need more tokens than their language's average premium. A quota set at the average runs out for these users.")

            left, right = st.columns([3, 2])
            with left:
                st.altair_chart(charts.buffer_band(buffers, label, coverage), width="stretch", theme=None)
            with right:
                shown = st.selectbox("Language to inspect", chosen, index=chosen.index("Hindi") if "Hindi" in chosen else 0, key="histogram_language")
                code = name_to_code[shown]
                row = buffers[buffers["lang_code"] == code].iloc[0]
                st.altair_chart(
                    charts.sentence_histogram(sentences[sentences["lang_code"] == code], shown, float(row["average"]), float(row["covered"]), coverage),
                    width="stretch",
                    theme=None,
                )
            st.caption(
                "A quota set at the average premium fits only about half of a language's sentences. The black tick is the premium that fits the share chosen above. "
                "These are single sentences: longer requests average out, so treat the buffer as an upper limit. "
                "Chart types (FT Visual Vocabulary): left, Distribution (box-plot style range with a covering tick); right, Distribution (histogram)."
            )
            st.markdown(
                f"**Takeaway:** A quota set at the average premium leaves about {pct(1 - share_fit)} of sentences short. Covering {pct(coverage)} of them takes {pct(lo['buffer_pct'])} to {pct(hi['buffer_pct'])} more tokens, "
                "so quotas need a buffer."
            )
            not_shown(
                "Single sentences, not whole documents: a long request averages out, so the real buffer is smaller than shown. Input tokens only.",
                "Each sentence premium divides by the English token count of the same sentence, so very short sentences make it noisy. The spread is for 200 sentences per language.",
                "Why a language varies more or less: we have no per-sentence features (vocabulary, names, numbers) to explain it.",
            )

            with st.expander("Table view of the values in these charts"):
                table = buffers[["language", "average", "p25", "p50", "p75", "covered", "buffer_pct"]].sort_values("buffer_pct", ascending=False)
                st.dataframe(
                    table,
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "language": "Language",
                        "average": st.column_config.NumberColumn("Average premium", format="%.2f"),
                        "p25": st.column_config.NumberColumn("25th percentile", format="%.2f", help="One in four sentences needs fewer tokens than this."),
                        "p50": st.column_config.NumberColumn("Median", format="%.2f", help="The middle sentence: half need fewer tokens, half need more."),
                        "p75": st.column_config.NumberColumn("75th percentile", format="%.2f", help="Three in four sentences need fewer tokens than this."),
                        "covered": st.column_config.NumberColumn(f"Covers {coverage:.0%}", format="%.2f"),
                        "buffer_pct": st.column_config.NumberColumn("Buffer", format="percent"),
                    },
                )
            st.download_button(
                "Download filtered data",
                data=buffers.drop(columns=["iso_15924"]).to_csv(index=False).encode("utf-8"),
                file_name="buffer_by_language_filtered.csv",
                mime="text/csv",
                key="buffer_download",
            )
        st.caption(SOURCE_SENTENCES)


# ------------------------------------------------------------------ story 4: pricing tiers


def render_tier_view() -> None:
    langs = langs_table()
    all_names = sorted(langs.loc[langs["lang_code"] != ENGLISH, "language"])
    mix = mix_table()

    with st.container(key="pricing_tiers"):
        st.header(story_titles()["pricing_tiers"])
        st.caption("Unit: premium (×) = tokens a language needs ÷ tokens English needs; overcharge (%) = how much more the tier price is than the language's real premium. "
            f"The heading uses the default cut-offs ({data.DEFAULT_TIER_BOUNDS[0]:.1f}× and {data.DEFAULT_TIER_BOUNDS[1]:.1f}×) on every tokeniser.")
        st.caption(f"Latest observation: {TOKEN_COUNTS_RUN}")
        how_to_use(
            "Pick a tokeniser with **← Previous** / **Next →**. Move the two handles on **Tier cut-offs** to decide where one tier ends and the next begins: "
            "the three tier cards, the shaded bands on the chart and the table on the right all update.",
            "Remove languages from **Languages served** to see how the tiers price a smaller market.",
            "Reading the chart: a dot far left of its black tick means that language pays well above its real cost.",
        )

        tokenizer_id = tokenizer_select("tier_tokenizer")
        slider_max = data.tier_slider_max(rows_for(tokenizer_id).query("lang_code != @ENGLISH"))
        if "tier_bounds" in st.session_state:  # keep earlier cut-offs inside the new tokeniser's range
            old = st.session_state["tier_bounds"]
            clamped = (min(float(old[0]), slider_max), min(float(old[1]), slider_max))
            if clamped != (float(old[0]), float(old[1])):
                st.session_state["tier_bounds"] = clamped
        bounds = st.slider(
            "Tier cut-offs (premium ×)",
            1.0,
            slider_max,
            data.DEFAULT_TIER_BOUNDS,
            0.1,
            key="tier_bounds",
            help="The two handles are the cut-offs between tiers, measured in premium (× English tokens). The scale ends at the costliest language's premium on this tokeniser, "
            "because a cut-off beyond it would change nothing. "
            "Languages up to the first handle are tier 1, up to the second handle tier 2, and the rest tier 3. "
            "Each tier charges the premium of its costliest language, so moving a handle changes the prices and the overcharge.",
        )
        st.caption(
            "Drag either handle: the three tier cards below and the shaded bands on the chart move with it. Everyone in a tier pays the same price, "
            "the premium of the tier's costliest language, so cheaper languages in the tier pay more than their real cost. That extra is the overcharge."
        )
        cards = st.container()
        chosen = st.multiselect("Languages served", all_names, default=all_names, key="tier_language_filter")
        english_note("It is the reference that every premium is measured against (always 1.0×), so it is not placed in a tier.")
        st.write(selected_line(chosen, len(all_names)))

        rows = rows_for(tokenizer_id)
        rows = rows[(rows["language"].isin(chosen)) & (rows["lang_code"] != ENGLISH)]
        label = TOKENIZER_LABELS[tokenizer_id]
        cut_offs = (float(bounds[0]), float(bounds[1]))
        if rows.empty:
            tier_cards(cards, cut_offs, None)
            st.info(EMPTY_MESSAGE)
        else:
            tiered = data.assign_tiers(rows, cut_offs)
            tier_cards(cards, cut_offs, tiered)
            flat = data.weighted_mean(tiered["over_flat"], tiered["lang_code"], mix)
            tier = data.weighted_mean(tiered["over_tier"], tiered["lang_code"], mix)
            latin = tiered[tiered["iso_15924"] == "Latn"]
            m = st.columns(3)
            m[0].metric("Overcharge, one price for all", pct(flat), help="Everyone pays the costliest selected language's multiplier. Equal language weights (placeholder).")
            m[1].metric("Overcharge, these tiers", pct(tier), help="Each tier is priced at its costliest language, so nobody is undercharged.")
            m[2].metric(
                "Other Latin-script languages in tier 1",
                f"{int((latin['tier'] == 1).sum())} of {len(latin)}" if len(latin) else "none selected",
                help="Tests whether script predicts the tier.",
            )

            left, right = st.columns([3, 2])
            with left:
                st.altair_chart(charts.tier_dumbbell(tiered, label, (float(bounds[0]), float(bounds[1]))), width="stretch", theme=None)
            with right:
                summary = (
                    tiered.groupby("tier")
                    .agg(price=("tier_price", "first"), languages=("language", lambda s: ", ".join(sorted(s))), over=("over_tier", "mean"))
                    .reset_index()
                )
                st.markdown("**Tiers, price (× English) and mean overcharge** (English = 1.00×, the reference)")
                lines = ["| Tier | Price | Languages | Overcharge |", "|---|---:|---|---:|"]
                for row in summary.itertuples():
                    lines.append(f"| {row.tier} | {row.price:.2f}× | {row.languages} | {pct(row.over)} |")
                st.markdown("\n".join(lines))
                empty = [n for n in (1, 2, 3) if n not in set(summary["tier"])]
                if empty:
                    st.caption(
                        "Empty: " + ", ".join(f"tier {n}" for n in empty) + ". No selected language has a premium in "
                        + ("that range" if len(empty) == 1 else "those ranges") + " on this tokeniser, so it has no price."
                    )
                st.caption(
                    "Moving a cut-off changes which languages share a tier. Prices are set at the costliest language in the tier, "
                    "so nobody is undercharged; the cost is the overcharge shown. "
                    "Chart type (FT Visual Vocabulary): Ranking (dot plot of languages ordered by premium, with a stem to the tier price)."
                )
            one_price = float(tiered["premium_vs_en"].max())
            if tier < flat:
                logic = (
                    f"**Three tiers reduce overcharging compared with a single price.** One price has to cover the costliest selected language ({times(one_price)}), so the average language pays {pct(flat)} more than its real cost. "
                    f"Cut-offs at {bounds[0]:.1f}× and {bounds[1]:.1f}× cut that to {pct(tier)}, because the cheaper languages no longer pay the price of the few expensive ones."
                )
            else:
                logic = (
                    f"**These cut-offs do not beat one price.** The average overcharge is {pct(tier)} with cut-offs at {bounds[0]:.1f}× and {bounds[1]:.1f}×, against {pct(flat)} for one price. "
                    "Move the handles so that the cheap languages are separated from the expensive ones."
                )
            st.markdown("**Takeaway:** " + logic)
            not_shown(
                "Prices are set at the costliest language of each tier, so nobody is undercharged; a real price list would also weigh willingness to pay, competitors and discounts.",
                "Averages use equal language weights (placeholder, not real usage). With real shares the overcharge figures would change.",
                f"Tiers are fitted to one tokeniser. The same language moves between tiers when the tokeniser changes (story 2 shows a swing of up to {facts().swing_ratio:.1f}-fold for {facts().swing_language}).",
            )
            st.download_button(
                "Download filtered data",
                data=tiered[["lang_code", "language", "script", "premium_vs_en", "tier", "tier_price", "over_tier", "over_flat"]].to_csv(index=False).encode("utf-8"),
                file_name="pricing_tiers_filtered.csv",
                mime="text/csv",
                key="tier_download",
            )
        st.caption(SOURCE_PREMIUM + " Language weights: data/source/language_mix.csv (equal-weight placeholder).")


def render_pricing_banner() -> None:
    """Marks stories 3 and 4 as implications of the finding above, not a second question."""
    with st.container(key="pricing_banner"):
        st.subheader("What this means for pricing")
        st.caption("The gap above is why one price or one quota is unfair. The next two sections test how to set quotas and prices around it.")


# ------------------------------------------------------------------ footer


def render_footer() -> None:
    with st.container(key="sources"):
        st.subheader("Sources and data refresh")
        st.markdown(
            f"**Last data refresh: {LAST_REFRESH}.** "
            f"Sentences: [FLORES+ devtest](https://huggingface.co/datasets/openlanguagedata/flores_plus) (Open Language Data Initiative, CC BY-SA 4.0), retrieved {FLORES_RETRIEVED}. "
            f"Token counts: tiktoken, Hugging Face tokeniser files and the Anthropic and Google token-counting APIs, run {TOKEN_COUNTS_RUN}. "
            "Published comparison values: `data/reference/published_premiums.csv`, transcribed from Petrov et al. (2023). "
            "Files, licences, keys and transforms are documented in `data_dictionary.md`; `bash run_all.sh` rebuilds every processed file."
        )
        st.markdown("**Chart types** are based on the Financial Times Visual Vocabulary: Ranking, Deviation, Change over time and Distribution.")
        st.markdown("**References**\n\n" + "\n".join(f"- {paper}" for paper in BACKGROUND_PAPERS))
