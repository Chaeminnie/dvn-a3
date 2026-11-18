"""Style guide page for checking components. Remove from the nav before submitting."""
import altair as alt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import style


def _swatches(pairs):
    cells = "".join(
        f"<div style='font-size:12px;color:{style.SUB}'><div style='width:88px;height:44px;border-radius:12px;"
        f"background:{h};box-shadow:inset 0 0 0 1px {style.LINE}'></div><div style='margin-top:6px;font-weight:600;color:{style.INK}'>{n}</div>{h}</div>"
        for n, h in pairs)
    st.markdown(f"<div style='display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px'>{cells}</div>", unsafe_allow_html=True)


def render(state):
    style.section("Style guide", "All shared components with the current colours. Edit the tokens in style.py to change them.")

    style.chart_title("Colour rule", "Blue = selected tokenizer · orange = focus language · grey = everything else")
    _swatches([("SELECTED", style.SELECTED), ("FOCUS", style.FOCUS), ("CONTEXT", style.CONTEXT),
               ("INK", style.INK), ("SUB", style.SUB), ("MUTED", style.MUTED), ("FILL", style.FILL), ("LINE", style.LINE)])
    style.chart_title("Families", "Fixed colour per tokenizer family")
    _swatches(list(style.FAMILY.items()))
    style.chart_title("Heatmap steps", "Light to dark")
    _swatches([(f"step {i}", c) for i, c in enumerate(style.SEQ)])

    style.chart_title("kpi_row()", "Three at most, label with unit")
    style.kpi_row([("Worst case", style.fmt_x(17.09), "Burmese on GPT-2"), ("Median language", style.fmt_x(1.6), None),
                   ("Pairs costing more than their script", style.fmt_pct(0.74), None)])
    style.chart_title("answer() · callout() · empty_state()", "")
    style.answer("<b>Answer: mostly the tokenizer.</b> One or two sentences in plain words.")
    style.callout("Even on the fairest tokenizer, Burmese is still 2.4× English.", "Next: what the remaining gap costs you →")
    style.empty_state()
    style.chart_title("table()", "For lookups; numbers right-aligned with units in the header")
    df = pd.DataFrame({"Language": ["Burmese", "Tamil", "English"], "Tokens vs English": [3.21, 2.01, 1.0],
                       "Tokens per sentence": [91, 57, 27]})
    style.table(df, **{"Tokens vs English": st.column_config.NumberColumn(format="%.2f×")})
    style.how_to_read("Explanation goes here.")
    style.not_shown("Point one.", "Point two.")
    style.chart_title("placeholder()", "Until the owner adds the chart")
    style.placeholder("Chart type · what it shows", "Owner", 140)

    p = state.d["prem"]
    d = p[p.tokenizer_id == state.tokenizer].sort_values("premium_vs_en").tail(8)
    a, b = st.columns(2, gap="large")
    with a:
        style.chart_title("Sample · Plotly bar", "Uses the sidebar tokenizer and focus language")
        fig = go.Figure(go.Bar(x=d.premium_vs_en, y=d.language, orientation="h",
                               marker_color=style.colours_for(d.language, focus=state.focus),
                               text=[style.fmt_x(v) for v in d.premium_vs_en], textposition="outside", cliponaxis=False))
        fig.update_xaxes(range=[0, d.premium_vs_en.max() * 1.2], ticksuffix="×")
        style.plotly_chart(style.plotly_theme(fig, x_title="Tokens vs English (×)", y_title=None, height=320))
    with b:
        style.chart_title("Sample · Altair line", "Same look from the Altair theme in style.py")
        g = state.d["gini"].copy()
        g = g[g.family.isin(["gpt", "gemma", "claude"])]
        ch = alt.Chart(g).encode(
            x=alt.X("release_date:T", title="Release date", axis=alt.Axis(format="%Y", values=[alt.DateTime(year=y) for y in range(2019, 2027)])),
            y=alt.Y("gini:Q", title="Gini (lower = fairer)"),
            color=alt.Color("family:N", title=None, scale=alt.Scale(domain=["gpt", "gemma", "claude"],
                                                                     range=[style.FAMILY[k] for k in ["gpt", "gemma", "claude"]])))
        style.altair_chart((ch.mark_line(strokeWidth=2.5) + ch.mark_circle(size=80, opacity=1)
                            + ch.mark_text(dy=-12).encode(text=alt.Text("gini:Q", format=".2f"), color=alt.value(style.INK))).properties(height=290))
