"""Tab 3: Absorb, adjust or switch? Owner: Amanda.

Two parts on one page:
1. A calculator based on Chaemin's prototype (language mix, service inputs, list price) that turns the token premium into a monthly bill and
   compares three options: absorb the extra cost, adjust plans and quotas, or switch model.
2. An illustrative pricing-tier chart: what one price for every language overcharges, against three tiers.

All widget keys start with "costs_". Defaults go in session_state first, then the widget has key= and no value=.
"""
from __future__ import annotations

import math
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

import data
import style

DEFAULT_ENGLISH_ONLY = 30.0  # % of users who only use English: assumed, not observed usage pattern
DEFAULT_BOUNDS = (1.5, 2.1)  # tier cut-offs (× English); best for the default tokenizer (o200k)
# Tiers use the sequential blue steps (light to dark) from the style guide.
TIER_COLOURS = [style.SEQ[3], style.SEQ[5], style.SEQ[6]]


# Prices
def _list_price(prices: pd.DataFrame, tokenizer: str) -> tuple[float, float, str]:
    """(input $/M, output $/M, source note). Official row valid today, otherwise the illustrative row."""
    today = pd.Timestamp(date.today())
    rows = prices[(prices["tokenizer_id"] == tokenizer) & (prices["source_tier"] == "official")].copy()
    start = pd.to_datetime(rows["valid_from"]).fillna(pd.Timestamp.min)
    end = pd.to_datetime(rows["valid_until"]).fillna(pd.Timestamp.max)
    rows = rows[(start <= today) & (end >= today)]
    if len(rows):
        r = rows.iloc[0]
        return float(r["input_usd_per_1m"]), float(r["output_usd_per_1m"]), f"Official list price ({r['provider']})."
    ill = prices[prices["tokenizer_id"] == "all"].iloc[0]
    p = float(ill["input_usd_per_1m"])
    return p, p, "No published list price for this tokenizer. Illustrative equal price, not a quote."


# Tiers
def assign_tiers(rows: pd.DataFrame, bounds: tuple[float, float]) -> pd.DataFrame:
    """Add tier (1-3), tier_price, flat_price and the overcharge of each. Price = costliest language in the tier."""
    out = rows.copy()
    out["tier"] = 1 + (out["premium"] > bounds[0]).astype(int) + (out["premium"] > bounds[1]).astype(int)
    out["tier_price"] = out.groupby("tier")["premium"].transform("max")
    out["flat_price"] = out["premium"].max()
    out["over_tier"] = out["tier_price"] / out["premium"] - 1
    out["over_flat"] = out["flat_price"] / out["premium"] - 1
    return out


def _weighted(values: pd.Series, weights: pd.Series) -> float:
    w = weights.fillna(0)
    return float((values * w).sum() / w.sum()) if w.sum() > 0 else float(values.mean())


def _slider_max(premiums: pd.Series) -> float:
    return max(3.0, float(math.ceil(premiums.max())))


def _tier_chart(df: pd.DataFrame, bounds: tuple[float, float], focus: str) -> alt.Chart:
    order = df.sort_values("premium", ascending=False)["language"].tolist()
    peak = float(df["premium"].max())
    xmax = peak * 1.9
    scale = alt.Scale(type="log", domain=[0.85, xmax])
    names = ["Tier 1", "Tier 2", "Tier 3"]
    colour = alt.Color("tier_name:N", scale=alt.Scale(domain=names, range=TIER_COLOURS), legend=None)
    y = alt.Y("language:N", sort=order, title=None, axis=alt.Axis(labelLimit=300, labelPadding=10))
    ticks = [t for t in (1, 1.5, 2, 3, 4, 6, 8) if t <= xmax]
    x_axis = alt.Axis(values=ticks, labelExpr="datum.label + '×'", title="Tokens compared with English (log scale)")

    d = df.assign(tier_name=df["tier"].map(lambda t: names[t - 1]),
                  dot_colour=[style.FOCUS if n == focus else TIER_COLOURS[t - 1] for n, t in zip(df["language"], df["tier"])],
                  dot_label=df["premium"].map(lambda v: f"{v:.2f}×"),
                  over_label=df["over_tier"].map(lambda v: f"+{v * 100:.0f}%"))
    bands = pd.DataFrame({"x0": [0.85, bounds[0], bounds[1]], "x1": [bounds[0], bounds[1], xmax], "tier_name": names})
    band = alt.Chart(bands).mark_rect(opacity=0.07).encode(
        x=alt.X("x0:Q", scale=scale, axis=x_axis), x2="x1:Q", color=alt.Color("tier_name:N", scale=alt.Scale(domain=names, range=TIER_COLOURS), legend=None))
    cuts = alt.Chart(pd.DataFrame({"x": list(bounds)})).mark_rule(strokeDash=[4, 4], color=style.MUTED).encode(
        x=alt.X("x:Q", scale=scale))
    flat = alt.Chart(pd.DataFrame({"x": [peak], "t": [f"One price: {peak:.2f}×"]}))
    flat_rule = flat.mark_rule(color=style.INK, strokeDash=[2, 3]).encode(x=alt.X("x:Q", scale=scale))
    flat_text = flat.mark_text(align="right", dx=-6, dy=-8, baseline="bottom", color=style.INK, fontWeight="bold",
                               fontSize=12).encode(x=alt.X("x:Q", scale=scale), y=alt.value(0), text="t:N")
    base = alt.Chart(d).encode(y=y)
    link = base.mark_rule(color=style.CONTEXT, strokeWidth=2).encode(
        x=alt.X("premium:Q", scale=scale), x2="tier_price:Q")
    dots = base.mark_circle(size=100, opacity=1).encode(x=alt.X("premium:Q", scale=scale),
                                                         color=alt.Color("dot_colour:N", scale=None, legend=None))
    tick = base.mark_tick(color=style.INK, thickness=3, size=16).encode(x=alt.X("tier_price:Q", scale=scale))
    dot_txt = base.mark_text(align="right", dx=-10, color=style.SUB, fontSize=12).encode(
        x=alt.X("premium:Q", scale=scale), text="dot_label:N")
    over_txt = base.mark_text(align="left", dx=10, color=style.INK, fontWeight="bold", fontSize=12).encode(
        x=alt.X("tier_price:Q", scale=scale), text="over_label:N")
    chart = alt.layer(band, cuts, flat_rule, link, dots, tick, dot_txt, over_txt, flat_text)
    return chart.properties(height=24 * len(d) + 70, padding={"left": 16, "right": 16, "top": 8, "bottom": 8})


# Language mix
def _reset_mix(mix: dict) -> None:
    for code, share in mix.items():
        st.session_state[f"costs_share_{code}"] = share


def render(state):
    d = state.d
    langs = d["langs"]
    ss = st.session_state
    style.section("Absorb, adjust or switch?",
                  "Enter your own language mix and see what the token premium costs you, then compare absorbing it, "
                  "tiered plans and quotas, and switching model.")

    # Premium per language on the chosen tokenizer
    prem_t = d["prem"][d["prem"]["tokenizer_id"] == state.tokenizer].set_index("lang_code")["premium_vs_en"]
    codes = langs["lang_code"].tolist()
    name_of = dict(zip(langs["lang_code"], langs["language"]))
    # Default mix: assumed, not observed. 30% English-only, the other 70% split equally over 14 languages.
    default_mix = {c: (DEFAULT_ENGLISH_ONLY if c == data.ENGLISH else round((100 - DEFAULT_ENGLISH_ONLY) / (len(codes) - 1), 1))
                   for c in codes}

    # Inputs
    for c in codes:
        ss.setdefault(f"costs_share_{c}", default_mix[c])
    ss.setdefault("costs_mau", 100_000)
    ss.setdefault("costs_rpu", 200)
    ss.setdefault("costs_budget", 100)
    ss.setdefault("costs_en_in", 500)
    ss.setdefault("costs_en_out", 300)
    ss.setdefault("costs_quota", 250_000)
    pin0, pout0, price_note = _list_price(d["prices"], state.tokenizer)
    ss.setdefault(f"costs_pin_{state.tokenizer}", pin0)
    ss.setdefault(f"costs_pout_{state.tokenizer}", pout0)

    others = [c for c in codes if c != data.ENGLISH]
    with st.container(border=True):
        st.markdown("**Your inputs**")
        # Language mix and English-only share
        st.markdown("**Language mix**")
        m1, m2 = st.columns([1, 2], gap="large")
        with m1:
            st.slider("English-only share (% of users who only use English)", 0.0, 100.0, step=0.5, format="%.1f%%",
                      key=f"costs_share_{data.ENGLISH}",
                      help="Default value is 30%. The remainder is split across the other 14 languages using the weights on the right.")
        with m2:
            with st.expander("Mix of the other languages (relative weights)", icon=":material/language:"):
                st.caption("Only the proportions matter. They are scaled to fill what the English-only share leaves. "
                           "The default is 30% English-only and equal weights for the rest. It is assumed, not observed usage pattern.")
                grid = st.columns(5)
                for i, c in enumerate(others):
                    grid[i % 5].number_input(name_of[c], min_value=0.0, max_value=100.0, step=1.0, format="%.1f",
                                             key=f"costs_share_{c}")
                st.button("Reset to default mix", on_click=_reset_mix, args=(default_mix,))

        c1, c2, c3 = st.columns(3, gap="large")
        with c1:
            st.markdown("**Users and requests**")
            st.number_input("Monthly active users", min_value=0, step=1000, key="costs_mau")
            st.number_input("Requests per user per month", min_value=0, step=10, key="costs_rpu")
            st.number_input("Quota per user (tokens a month, 0 for none)", min_value=0, step=10_000, key="costs_quota")
        with c2:
            st.markdown("**Tokens per request**")
            st.number_input("English input tokens", min_value=0, step=50, key="costs_en_in")
            st.number_input("English output tokens", min_value=0, step=50, key="costs_en_out")
        with c3:
            st.markdown("**Price**")
            p1, p2 = st.columns(2)
            p1.number_input("Input $ per 1M", min_value=0.0, step=0.05, format="%.2f", key=f"costs_pin_{state.tokenizer}")
            p2.number_input("Output $ per 1M", min_value=0.0, step=0.05, format="%.2f", key=f"costs_pout_{state.tokenizer}")
            st.number_input("Budget to compare ($)", min_value=1, step=50, key="costs_budget")
        st.caption(f"{price_note} Prices are for {data.TOKENIZER[state.tokenizer]}.")

    # English-only share is fixed; the other languages share what is left, in proportion to their weights
    eng_share = float(ss[f"costs_share_{data.ENGLISH}"]) / 100
    weights = pd.Series({c: float(ss[f"costs_share_{c}"]) for c in others})
    if weights.sum() <= 0:
        weights[:] = 1.0  # all weights zero: fall back to equal weights
    w = pd.concat([pd.Series({data.ENGLISH: eng_share}), (1 - eng_share) * weights / weights.sum()]).reindex(codes)
    pin, pout = float(ss[f"costs_pin_{state.tokenizer}"]), float(ss[f"costs_pout_{state.tokenizer}"])
    mau, rpu, en_in, en_out, quota = (ss["costs_mau"], ss["costs_rpu"], ss["costs_en_in"], ss["costs_en_out"],
                                      ss["costs_quota"])

    prem = prem_t.reindex(codes)
    cost_en = (en_in * pin + en_out * pout) / 1e6  # one English request
    volume = mau * rpu
    blended = float((w * prem).sum())
    bill = blended * cost_en * volume
    english_bill = cost_en * volume
    extra = bill - english_bill
    extra_pct = blended - 1

    # Quota: a user in language L runs out when requests at the quota is below the requests they make
    tokens_req = (en_in + en_out) * prem
    out_of_quota = (quota / tokens_req.where(tokens_req > 0) < rpu) if quota > 0 else pd.Series(False, index=codes)
    run_out = float(w[out_of_quota].sum())

    # Tiers, over the non-English languages the sidebar filter allows
    tier_rows = pd.DataFrame({"lang_code": codes, "language": [name_of[c] for c in codes], "premium": prem.values,
                              "weight": w.values})
    tier_rows = tier_rows[(tier_rows["lang_code"] != data.ENGLISH) & tier_rows["language"].isin(state.languages)]
    tier_rows = tier_rows.dropna(subset=["premium"]).reset_index(drop=True)

    # Switch model: fewest tokens on your mix, compared on each tokenizer's own English baseline
    cmp = []
    for t in data.TOKENIZER:
        if t in data.IDENTICAL:
            continue
        p = d["prem"][d["prem"]["tokenizer_id"] == t].set_index("lang_code")["premium_vs_en"].reindex(codes)
        if p.isna().any():
            continue
        b = float((w * p).sum())
        row = {"id": t, "Tokenizer": data.TOKENIZER[t], "Blended premium": b}
        twin = [k for k, v in data.IDENTICAL.items() if v == t]
        if twin:
            row["Tokenizer"] += f" = {data.TOKENIZER[twin[0]]}"
        cmp.append(row)
    cmp = pd.DataFrame(cmp)
    best = cmp.loc[cmp["Blended premium"].idxmin()]
    tokens_change = best["Blended premium"] / blended - 1

    with st.container():
        style.kpi_row([
            ("Blended premium", style.fmt_x(blended, 2),
             "Average tokens per request compared with English, weighted by your language mix."),
            ("Monthly bill", f"${bill:,.0f}", f"{mau:,} users × {rpu:,} requests, at the prices you entered."),
            ("Extra vs English", f"+{style.fmt_pct(extra_pct)}",
             f"${extra:,.0f} a month more than the same users would cost if everyone wrote English."),
        ])
        o1, o2, o3 = st.columns(3)
        o1.metric("Absorb (extra a month)", f"${extra:,.0f}", f"{style.fmt_pct(extra_pct)} over an all-English mix",
                  delta_color="inverse", delta_arrow="off",
                  help="Keep prices as they are and pay the extra tokens yourself.")
        if len(tier_rows):
            bounds = ss.get("costs_bounds", DEFAULT_BOUNDS)
            t_all = assign_tiers(tier_rows, bounds)
            over_t, over_f = _weighted(t_all["over_tier"], t_all["weight"]), _weighted(t_all["over_flat"], t_all["weight"])
            o2.metric("Adjust plans (overcharge)", f"+{over_t * 100:.0f}%",
                      f"vs +{over_f * 100:.0f}% for one price", delta_color="off", delta_arrow="off",
                      help="Average overcharge across the languages in the tier chart below, weighted by your mix. "
                           "Move the cut-offs in the chart to change it.")
        else:
            o2.metric("Adjust plans and quotas", "-", help="Pick at least one script group in the sidebar.")
        if best["id"] == state.tokenizer:
            o3.metric("Switch model", "Already fairest", help="No other tokenizer has a lower blended premium on your mix.")
        else:
            o3.metric("Switch model", data.TOKENIZER[best["id"]], f"{tokens_change * 100:+.0f}% tokens on your mix",
                      delta_color="inverse", help=f"{best['Tokenizer']}: the lowest blended premium on your mix. "
                      "Real bills also depend on each model's price.")
        if quota > 0:
            hit = [name_of[c] for c in codes if out_of_quota[c]]
            where = f" ({', '.join(hit[:4])}{', ...' if len(hit) > 4 else ''})" if hit else ""
            st.caption(f"At a quota of {quota:,} tokens a month, {style.fmt_pct(run_out)} of users run out before "
                       f"{rpu:,} requests{where}.")
        fp = prem.get(next(c for c in codes if name_of[c] == state.focus), float("nan"))
        if pd.notna(fp) and fp > 0 and cost_en > 0:
            budget = ss["costs_budget"]
            n_en = budget / cost_en
            st.caption(f"Budget view: ${budget:,.0f} buys about {n_en:,.0f} English requests but only {n_en / fp:,.0f} in "
                       f"{state.focus} ({style.fmt_pct(1 / fp)} of English) on {data.TOKENIZER[state.tokenizer]}.")

    with st.expander("Bill by language", icon=":material/table:"):
        tbl = pd.DataFrame({
            "Language": [name_of[c] for c in codes],
            "Share of users": w.values,
            "Premium": prem.values,
            "Tokens per request": tokens_req.values,
            "Cost per request ($)": (prem * cost_en).values,
            "Monthly cost ($)": (w * prem * cost_en * volume).values,
        }).sort_values("Premium", ascending=False)
        style.table(tbl,
                    **{"Share of users": st.column_config.NumberColumn(format="percent"),
                       "Premium": st.column_config.NumberColumn(format="%.2f×"),
                       "Tokens per request": st.column_config.NumberColumn(format="%,.0f"),
                       "Cost per request ($)": st.column_config.NumberColumn(format="$%.4f"),
                       "Monthly cost ($)": st.column_config.NumberColumn(format="$%,.0f")})
    with st.expander("Compare tokenizers on your mix", icon=":material/compare_arrows:"):
        c2 = cmp.copy()
        c2["Tokens vs current"] = c2["Blended premium"] / blended - 1
        c2["Monthly bill at your prices ($)"] = c2["Blended premium"] * cost_en * volume
        listed = []
        for t in c2["id"]:
            a, b_, note = _list_price(d["prices"], t)
            listed.append(((en_in * a + en_out * b_) / 1e6 * volume * float(c2.loc[c2["id"] == t, "Blended premium"].iloc[0]))
                          if note.startswith("Official") else None)
        c2["Monthly bill at list price ($)"] = listed
        style.table(c2.drop(columns="id").sort_values("Blended premium"),
                    **{"Blended premium": st.column_config.NumberColumn(format="%.2f×"),
                       "Tokens vs current": st.column_config.NumberColumn(format="%+.0f%%"),
                       "Monthly bill at your prices ($)": st.column_config.NumberColumn(format="$%,.0f"),
                       "Monthly bill at list price ($)": st.column_config.NumberColumn(format="$%,.0f")})
        st.caption("List price is shown only where the provider publishes one. English token counts are assumed "
                   "to be the same on every tokenizer.")

    # Tier chart
    if not len(tier_rows):
        style.empty_state()
        return
    smax = _slider_max(tier_rows["premium"])
    cur = ss.get("costs_bounds", DEFAULT_BOUNDS)
    ss["costs_bounds"] = tuple(round(min(max(v, 1.0), smax), 1) for v in cur)  # keep inside this tokenizer's range
    bounds = st.slider("Tier cut-offs (tokens compared with English)", 1.0, smax, step=0.1, key="costs_bounds")
    t = assign_tiers(tier_rows, bounds)
    over_t, over_f = _weighted(t["over_tier"], t["weight"]), _weighted(t["over_flat"], t["weight"])
    peak_lang = t.loc[t["premium"].idxmax(), "language"]

    style.chart_title("What one price vs three tiers overcharges",
                      f"Dot = what the language really costs (orange = {state.focus}). Black tick = the price its tier charges. Label = overcharge. "
                      f"Cut-offs at {bounds[0]:.1f}× and {bounds[1]:.1f}×, {data.TOKENIZER[state.tokenizer]}.")
    edges = [f"up to {bounds[0]:.1f}×", f"{bounds[0]:.1f}× to {bounds[1]:.1f}×", f"over {bounds[1]:.1f}×"]
    tier_cols, tier_lines = [], []
    for i in (1, 2, 3):
        m = t[t["tier"] == i]
        tier_cols.append((f"Tier {i} price · {edges[i - 1]}", style.fmt_x(m["premium"].max(), 2) if len(m) else "-"))
        tier_lines.append(f"**Tier {i}:** " + (", ".join(m.sort_values("premium")["language"]) if len(m) else "no languages"))
    style.kpi_row(tier_cols)
    st.caption("  \n".join(tier_lines))
    style.altair_chart(_tier_chart(t, bounds, state.focus))
    style.kpi_row([
        ("One price covers", style.fmt_x(t["flat_price"].iloc[0], 2), f"The costliest language shown: {peak_lang}."),
        ("Overcharge, one price", f"+{over_f * 100:.0f}%", "Average, weighted by your language mix."),
        ("Overcharge, three tiers", f"+{over_t * 100:.0f}%", "Average, weighted by your language mix."),
    ])
    if over_t < over_f:
        style.callout("Three tiers overcharge less than one price",
                      f"One price has to cover the costliest language ({t['flat_price'].iloc[0]:.1f}×, {peak_lang}), so the "
                      f"average language pays {over_f * 100:.0f}% more than its real cost. Cut-offs at {bounds[0]:.1f}× and "
                      f"{bounds[1]:.1f}× cut that to {over_t * 100:.0f}%, because the cheaper languages no longer pay for "
                      f"the few expensive ones.")
    else:
        style.callout("These cut-offs do not beat one price",
                      f"With cut-offs at {bounds[0]:.1f}× and {bounds[1]:.1f}× the average overcharge is {over_t * 100:.0f}%, "
                      f"against {over_f * 100:.0f}% for one price. Move the cut-offs so that the expensive languages sit "
                      f"alone in the top tier.")
    style.how_to_read(
        "Each row represents a language. The **dot** (orange for the focus language)shows its actual token premium, or how many tokens the same text "
        "requires compared with English (x-axis is logarithmic). The **black tick** marks the price "
        "charged for that language's tier, based on the costliest language in the tier. The gap between the "
        "dot and tick shows the overcharge, and the **label** reports it as a percentage. The shaded bands show "
        "three pricing tiers, with darker blue representing higher tiers, with boundaries marked by dashed lines. "
        "The dotted line at the right shows the **one price** that would be charged "
        "if all languages were priced at the most expensive language's premium.\n\n"
        "The slider above the chart allows you to adjust the two tier boundaries. Languages are reassigned instantly,  "
        "and tier prices and overcharge figures update automatically. The slider starts at 1.5× and 2.1×, "
        "which minimise average overcharge for the default tokenizer (o200k). "
        "Average overcharge is weighted by the language mix entered above,  "
        "and only languages included in the selected script groups are shown.")

    style.not_shown(
        "**Real usage:** the default mix (30% English-only, with the remainder split equally across other languages) is assumed, not an observed usage pattern. Adjust it above to explore alternatives.",
        "**Output length:** output tokens are assumed to grow at the same rate as input tokens, and English token counts are assumed to be identical across tokenizers.",
        "**Prices:** some tokenizers use illustrative prices because not all providers publish a list price. ",
        "**Tier design:** three tiers are fixed, and cut-offs are chosen manually rather than optimised for a specific language mix.",
        "**Sampling error:** token premiums come from a 200-sentence sample and may vary by up to about 3%.",
        "**Model switch:** the recommendation to switch models compares token counts only, not model quality, speed, language support, or pricing structure.",
        "**Other costs:** Discounts, taxes, willingness to pay, and the underlying cost of running the model itself are excluded.",
    )
