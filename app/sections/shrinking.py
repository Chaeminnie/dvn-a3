"""Tab 2: Is it shrinking? Owner: Saloni.

Question for this tab: are newer tokenizers fairer than older ones, family by family?
Numbers come from data/processed/tokenizer_gini.csv (data.load()["gini"]) for the cards and chart,
and from data/processed/token_premium.csv (data.load()["prem"]) for the focus-language line.
Nothing is hard-coded: every number is computed from those two files.
"""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

import style

SHORT = {"gpt": "GPT", "gemma": "Gemma", "qwen": "Qwen", "claude": "Claude",
         "llama": "Llama", "mistral": "Mistral", "gemini": "Gemini"}
SINGLE = "Single version (no trend)"
IMPROVE = 0.01  # a family "improved" if its newest tokenizer scores more than 1% lower than its oldest

MEASURES = {
    "Gini across languages (lower = fairer)": dict(
        col="gini", short="Gini", title="Inequality across languages, older → newer",
        axis="Gini across languages (0 = every language pays the same)",
        fmt=lambda v: f"{v:.2f}", baseline="gini_byte_baseline",
        how=("**Gini across languages** scores how unequal the token premium is across the languages: "
             "0 means every language pays the same, higher means a wider gap.")),
    "Worst-language premium (× English)": dict(
        col="max_premium", short="Worst premium", title="Worst-language premium, older → newer",
        axis="Worst language: tokens vs English (×)",
        fmt=lambda v: style.fmt_x(v, 1), baseline=None,
        how=("**Worst-language premium** is the highest tokens-vs-English ratio of any language "
             "on that tokenizer (English = 1×).")),
    "Median-language premium (× English)": dict(
        col="median_premium", short="Median premium", title="Median-language premium, older → newer",
        axis="Median language: tokens vs English (×)",
        fmt=lambda v: style.fmt_x(v, 1), baseline=None,
        how=("**Median-language premium** is the middle language's tokens-vs-English ratio "
             "on that tokenizer (English = 1×).")),
}


def _family_changes(g: pd.DataFrame, col: str) -> pd.DataFrame:
    """Oldest vs newest tokenizer in each family that has two or more, on the chosen measure."""
    rows = []
    for fam, grp in g.groupby("family"):
        if len(grp) < 2:
            continue
        grp = grp.sort_values("release_date")
        a, b = grp.iloc[0], grp.iloc[-1]
        rows.append(dict(family=fam, first=a["tokenizer"], last=b["tokenizer"],
                         v_first=a[col], v_last=b[col], change=b[col] / a[col] - 1))
    return pd.DataFrame(rows)


def _names(df: pd.DataFrame) -> str:
    return ", ".join(SHORT.get(f, str(f).title()) for f in df["family"])


def render(state):
    # Empty filter state: show a message instead of an error or a blank page.
    if not state.languages:
        style.section("Is it shrinking?", "Newer tokenizers versus older ones, family by family.")
        style.empty_state()
        return

    head = st.container()  # filled in below, once the measure is known

    g_all = state.d["gini"].sort_values("release_date").reset_index(drop=True)
    prem = state.d["prem"]

    # Interactions (the sidebar tokenizer is a third one: it rings a dot in the chart)
    c1, c2 = st.columns([3, 2])
    measure = c1.selectbox("Measure", list(MEASURES), key="shrink_measure")
    hide_single = c2.toggle("Hide single-version families", key="shrink_hide_single")
    m = MEASURES[measure]
    col = m["col"]

    # ---- numbers (all computed from tokenizer_gini.csv) ----
    ch = _family_changes(g_all, col)
    if ch.empty:
        with head:
            style.section("Is it shrinking?", "Newer tokenizers versus older ones, family by family.")
        style.empty_state("No tokenizer family has two or more versions in the data.")
        return

    improved = ch[ch["change"] < -IMPROVE]
    flat = ch[ch["change"].abs() <= IMPROVE]
    worse = ch[ch["change"] > IMPROVE]
    takeaway = f"Newer versions are fairer in {len(improved)} of {len(ch)} tokenizer families on this measure"
    if len(flat):
        takeaway += f"; {_names(flat)} did not change"
    if len(worse):
        takeaway += f"; {_names(worse)} got worse"
    with head:
        style.section("Is it shrinking?", takeaway + ".")

    if len(improved):
        top = improved.loc[improved["change"].idxmin()]
        big = f"{SHORT.get(top['family'], top['family'])} · {style.fmt_pct(top['change'])}"
        big_help = f"{top['first']} → {top['last']}: {m['fmt'](top['v_first'])} → {m['fmt'](top['v_last'])}."
    else:
        big, big_help = "None", "No family scored more than 1% lower on its newest tokenizer."

    low = g_all[col].min()
    best = g_all[(g_all[col] - low).abs() < 1e-9]
    fair_name = best["tokenizer"].iloc[0]
    fair_help = f"Lowest value of the selected measure among the {len(g_all)} tokenizers."
    if len(best) > 1:
        fair_help += f" Tied with {', '.join(best['tokenizer'].iloc[1:])}."

    style.kpi_row([
        ("Families that improved", f"{len(improved)} of {len(ch)}",
         "Families with two or more tokenizers. Improved = the newest tokenizer scores more than 1% lower than the oldest."),
        ("Biggest improvement", big, big_help),
        ("Fairest tokenizer", f"{fair_name} · {m['fmt'](low)}", fair_help),
    ])

    # ---- chart ----
    g = g_all.copy()
    g["value"] = g[col]
    g["label"] = g["value"].map(m["fmt"])
    g["multi"] = g.groupby("family")["tokenizer_id"].transform("count") >= 2
    g["fam_name"] = g["family"].map(lambda f: SHORT.get(f, str(f).title()))
    g["group"] = g["fam_name"].where(g["multi"], SINGLE)
    singles = sorted(g.loc[~g["multi"], "fam_name"].unique())
    if hide_single:
        g = g[g["multi"]]

    multi_fams = [f for f in SHORT if ((g["family"] == f) & g["multi"]).any()]
    domain = [SHORT[f] for f in multi_fams]
    colours = [style.FAMILY.get(f, style.CONTEXT) for f in multi_fams]
    if (~g["multi"]).any():
        domain.append(SINGLE)
        colours.append(style.CONTEXT)

    x = alt.X("release_date:T", title="Tokenizer release date",
              axis=alt.Axis(format="%Y", tickCount="year"), scale=alt.Scale(padding=24))
    y = alt.Y("value:Q", title=m["axis"], scale=alt.Scale(zero=True))
    colour = alt.Color("group:N", scale=alt.Scale(domain=domain, range=colours),
                       legend=alt.Legend(title=None))
    tip = [alt.Tooltip("tokenizer:N", title="Tokenizer"),
           alt.Tooltip("release_date:T", title="Released", format="%d %b %Y"),
           alt.Tooltip("label:N", title=m["short"])]

    # dashed baseline: the byte baseline for Gini, English = 1x for the premium measures
    if m["baseline"]:
        base_v = float(g_all[m["baseline"]].iloc[0])
        base_txt = f"Byte baseline {base_v:.2f}"
    else:
        base_v, base_txt = 1.0, "English = 1×"
    bl = pd.DataFrame({"release_date": [g["release_date"].min()], "value": [base_v], "t": [base_txt]})
    rule = alt.Chart(bl).mark_rule(strokeDash=[5, 4], color=style.MUTED).encode(y=y)
    rule_txt = alt.Chart(bl).mark_text(align="left", dx=6, dy=-8, color=style.MUTED, fontSize=12).encode(
        x=x, y=y, text="t:N")

    lines = alt.Chart(g).mark_line(strokeWidth=2.5).encode(x=x, y=y, color=colour, detail="family:N")
    points = alt.Chart(g).mark_point(filled=True, size=90, opacity=1).encode(x=x, y=y, color=colour, tooltip=tip)

    # value label on every dot (Gemma sits just below its dot so it does not collide with GPT-4o)
    text_kw = dict(fontSize=12, fontWeight="bold", color=style.INK)
    above = alt.Chart(g[g["family"] != "gemma"]).mark_text(dy=-13, **text_kw).encode(x=x, y=y, text="label:N")
    below = alt.Chart(g[g["family"] == "gemma"]).mark_text(dy=15, **text_kw).encode(x=x, y=y, text="label:N")

    layers = [rule, rule_txt, lines, points, above, below]
    sel = g[g["tokenizer_id"] == state.tokenizer]
    if len(sel):
        layers.append(alt.Chart(sel).mark_point(filled=False, size=300, stroke=style.INK, strokeWidth=2)
                      .encode(x=x, y=y))
    chart = alt.layer(*layers).properties(height=style.CHART_HEIGHT)

    n_lang = int(g_all["n_languages"].iloc[0])
    n_sent = int(prem["n_sentences"].iloc[0])
    y0, y1 = g_all["release_date"].min().year, g_all["release_date"].max().year
    style.chart_title(
        m["title"],
        f"{m['axis']}. {n_lang} languages × {n_sent} FLORES+ sentences each; tokenizers released {y0}–{y1}. "
        f"One line per family, older to newer; the ring marks the tokenizer chosen in the sidebar. "
        f"Grey dots ({', '.join(singles) or 'none'}) have a single tokenizer, so they cannot show a trend.")
    style.altair_chart(chart)

    # table: the same numbers, with tokenizer names
    style.chart_title("Change by family", "Oldest vs newest tokenizer in each family with two or more.")
    tbl = pd.DataFrame({
        "Family": ch["family"].map(lambda f: SHORT.get(f, str(f).title())),
        "Older version": ch["first"],
        "Newer version": ch["last"],
        f"{m['short']} (older)": ch["v_first"].map(m["fmt"]),
        f"{m['short']} (newer)": ch["v_last"].map(m["fmt"]),
        "Change": ch["change"].map(style.fmt_pct),
    })
    style.table(tbl)

    # ---- bridge to the next tab ----
    if state.focus == "English":
        bridge = "English is the baseline: 1.0× on every tokenizer."
    else:
        r = prem[(prem["tokenizer_id"] == best["tokenizer_id"].iloc[0]) & (prem["language"] == state.focus)]
        bridge = (f"Even on the fairest tokenizer by this measure ({fair_name}), {state.focus} still needs "
                  f"{style.fmt_x(r['premium_vs_en'].iloc[0])} the tokens of English." if len(r) else
                  "Pick a focus language to see what the remaining gap looks like.")
    style.callout(bridge, "Next: what the remaining gap costs you, and your three options →")

    style.how_to_read(
        "Each line is one tokenizer family: older versions on the left, newer on the right. "
        "A line that slopes down means newer versions are fairer across languages.\n\n"
        f"{m['how']}\n\n"
        "The dashed line is the baseline: "
        + ("the Gini the languages would have if cost followed text size in bytes exactly "
           "(see data_dictionary.md)." if m["baseline"] else "English, which is 1× by definition.")
        + " The number on every dot is its value; the table below the chart lists names and dates.")
    style.not_shown(
        "Why a tokenizer changed. The data holds scores and release dates, not design decisions.",
        "A long trend. Each family has two or three tokenizers, so read this as a pattern in this "
        "sample, not a law.",
        "Qwen 2.5 and Qwen 3 give identical token counts on all sentences, and so do Gemma 3 and "
        "Gemini 3.8 Flash, so a flat line reflects identical counts rather than a failed redesign.",
        f"Real-world text. The scores use {n_lang} languages and {n_sent} FLORES+ sentences each "
        "(sampling error up to about 3%).",
        "Whether a service has switched. A newer release date does not mean every product uses that tokenizer.",
        "Money. The scores compare languages with each other; the next tab turns them into cost.",
    )
