"""Tab 1: Script or tokenizer? Owner: Chandan.

Charts A and B ported from the `chandan` branch (dashboards/chandan/charts.py),
rewired to the shared sidebar state and the colours/theme in style.py.
"""
import math

import plotly.graph_objects as go
import streamlit as st

import style
from data import IDENTICAL, TOKENIZER, dedupe


def _ranking(df, focus):
    """A. Token premium per language for one tokenizer, biggest at the top."""
    d = df.sort_values("premium_vs_en")  # Plotly draws horizontal bars bottom-up
    colours = [style.FOCUS if lang == focus else style.SELECTED for lang in d["language"]]

    fig = go.Figure(go.Bar(
        x=d["premium_vs_en"], y=d["language"], orientation="h",
        marker=dict(color=colours),
        text=[style.fmt_x(p) for p in d["premium_vs_en"]],
        textposition="outside", textfont=dict(color=style.INK, size=12), cliponaxis=False,
        customdata=d[["mean_tokens_per_sentence", "total_tokens"]],
        hovertemplate="<b>%{y}</b><br>%{x:.2f}× English<br>"
                      "%{customdata[0]:.0f} tokens per sentence<br>"
                      "%{customdata[1]:,} tokens in total<extra></extra>",
        showlegend=False,
    ))
    fig.add_vline(x=1, line=dict(color=style.MUTED, width=1, dash="dot"))
    fig.add_annotation(x=1, y=1, yref="paper", yanchor="bottom", text="English = 1×",
                       showarrow=False, font=dict(size=11, color=style.MUTED))

    height = max(260, 28 * len(d) + 90)
    fig = style.plotly_theme(fig, x_title="Tokens vs English", y_title=None, height=height)
    fig.update_xaxes(range=[0, d["premium_vs_en"].max() * 1.15], ticksuffix="×")
    fig.update_yaxes(showgrid=False)
    return fig


def _label_positions(points):
    """Pick a text position per language so neighbouring labels don't sit on each other."""
    pos = {lang: "middle right" for lang in points["language"]}
    pos["English"] = "bottom right"
    for a, b in [("Arabic", "Amharic"), ("Hindi", "Thai"), ("Tamil", "Burmese")]:
        pa = points[points["language"] == a]
        pb = points[points["language"] == b]
        if pa.empty or pb.empty:
            continue
        a_high = pa["premium_vs_en"].iloc[0] >= pb["premium_vs_en"].iloc[0]
        pos[a] = "top center" if a_high else "bottom center"
        pos[b] = "bottom center" if a_high else "top center"
    return pos


def _scatter(prem, tok_id, tok_name, focus, langs):
    """B. Byte premium (the script) against token premium (the bill), one dot per language."""
    data = prem[prem["language"].isin(langs)]
    sel = data[data["tokenizer_id"] == tok_id]
    twin = {**IDENTICAL, **{v: k for k, v in IDENTICAL.items()}}.get(tok_id)
    ctx = dedupe(data)
    ctx = ctx[~ctx["tokenizer_id"].isin([tok_id, twin])]

    fig = go.Figure()

    # The "script decides everything" line: tokens grow exactly as fast as bytes.
    fig.add_trace(go.Scatter(
        x=[0.85, 5], y=[0.85, 5], mode="lines",
        line=dict(color=style.MUTED, width=1.5, dash="dash"),
        name="Script only", hoverinfo="skip",
    ))

    fig.add_trace(go.Scatter(
        x=ctx["byte_premium_vs_en"], y=ctx["premium_vs_en"], mode="markers",
        marker=dict(size=7, color=style.CONTEXT, opacity=0.6),
        name="Other tokenizers",
        customdata=ctx[["language", "tokenizer"]],
        hovertemplate="<b>%{customdata[0]}</b> on %{customdata[1]}<br>"
                      "bytes %{x:.2f}× · tokens %{y:.2f}×<extra></extra>",
    ))

    # Label only the languages that stand apart; the cluster near 1× is noted in the caption.
    pos = _label_positions(sel)
    labelled = sel["byte_premium_vs_en"].ge(1.6) | sel["language"].eq("English")
    rest = sel[sel["language"] != focus]
    fig.add_trace(go.Scatter(
        x=rest["byte_premium_vs_en"], y=rest["premium_vs_en"], mode="markers+text",
        marker=dict(size=11, color=style.SELECTED, line=dict(width=2, color=style.SURFACE)),
        text=[lang if labelled[i] else "" for i, lang in rest["language"].items()],
        textposition=[pos[lang] for lang in rest["language"]],
        textfont=dict(color=style.INK, size=12),
        name=tok_name,
        customdata=rest[["language"]],
        hovertemplate="<b>%{customdata[0]}</b><br>bytes %{x:.2f}× · tokens %{y:.2f}×<extra></extra>",
    ))

    f = sel[sel["language"] == focus]
    if not f.empty:
        fig.add_trace(go.Scatter(
            x=f["byte_premium_vs_en"], y=f["premium_vs_en"], mode="markers+text",
            marker=dict(size=15, color=style.FOCUS, line=dict(width=2, color=style.SURFACE)),
            text=[f"{focus} {f['premium_vs_en'].iloc[0]:.1f}×"],
            textposition=pos.get(focus, "middle right"),
            textfont=dict(color=style.INK, size=12),
            name=focus,
            hovertemplate=f"<b>{focus}</b><br>bytes %{{x:.2f}}× · tokens %{{y:.2f}}×<extra></extra>",
        ))

    fig.add_annotation(xref="paper", yref="paper", x=0.01, y=0.99, xanchor="left", yanchor="top",
                       text="Above the line: the tokenizer adds cost",
                       showarrow=False, align="left", font=dict(size=11, color=style.MUTED))

    # Log scales because these are ratios: 2× to 4× is the same step as 4× to 8×.
    # Fixed ranges so switching tokenizer moves the dots instead of the axes.
    fig = style.plotly_theme(fig, x_title="Text size vs English (UTF-8 bytes)",
                             y_title="Tokens vs English", height=460)
    ticks_x = [1, 1.5, 2, 3, 4]
    ticks_y = [1, 2, 3, 5, 10, 20]
    fig.update_xaxes(type="log", range=[math.log10(0.85), math.log10(5)],
                     tickvals=ticks_x, ticktext=[f"{t:g}×" for t in ticks_x])
    fig.update_yaxes(type="log", range=[math.log10(0.85), math.log10(20)],
                     tickvals=ticks_y, ticktext=[f"{t:g}×" for t in ticks_y])
    return fig


def render(state):
    prem = state.d["prem"]
    tok_id, tok_name, focus = state.tokenizer, TOKENIZER[state.tokenizer], state.focus

    # KPIs follow the focus language regardless of the script pills (focus is its own control).
    pf = prem[prem["language"] == focus]
    row = pf[pf["tokenizer_id"] == tok_id].iloc[0]
    script_alone = row["byte_premium_vs_en"]  # language property, same on every tokenizer
    on_selected = row["premium_vs_en"]
    swing = pf["premium_vs_en"].max() / pf["premium_vs_en"].min()

    style.section("Is it the script or the tokenizer?",
                  f"{focus}'s script adds {style.fmt_x(script_alone)} before any tokenizer, "
                  f"but the tokenizer you pick swings its bill {style.fmt_x(swing)}.")

    if not state.languages:
        return style.empty_state()

    style.kpi_row([
        (f"Script alone · {focus}", style.fmt_x(script_alone), "Text size vs English in UTF-8 bytes. The floor the script sets, before any tokenizer."),
        (f"On {tok_name}", style.fmt_x(on_selected), "Tokens vs English for the focus language on the selected tokenizer."),
        (f"Tokenizer swing · {focus}", style.fmt_x(swing), "Most expensive divided by cheapest tokenizer for this language."),
    ])

    d = prem[(prem["tokenizer_id"] == tok_id) & prem["language"].isin(state.languages)]
    a, b = st.columns(2, gap="large")
    with a:
        style.chart_title("Who pays the most?", f"Token cost vs English on {tok_name}. Orange is your focus language.")
        style.plotly_chart(_ranking(d, focus))
    with b:
        style.chart_title("Is it the script?",
                          "Each dot is a language. Dots above the dashed line cost more than their script alone explains.")
        style.plotly_chart(_scatter(prem, tok_id, tok_name, focus, state.languages))

    style.how_to_read(
        "**Left:** each bar is one language's token cost against English on the selected tokenizer. "
        "1× means the same number of tokens as English. "
        "**Right:** the across is how much longer the text is in raw bytes (the script), the up is how many "
        "tokens it actually costs. The dashed line is where a tokenizer only charges for the extra bytes. "
        "A dot sitting above the line means the tokenizer adds cost on top of the script. "
        "Grey dots are the same languages on the other tokenizers, for context.")
    style.not_shown(
        "Prices. These are token ratios, not dollars. The money side is on the 'Absorb, adjust or switch?' tab.",
        "Whether the gap is closing. That is the next tab, 'Is it shrinking?'.",
        "Exact figures. They come from a 200-sentence FLORES+ sample, so expect wobble of a few percent.",
        "Within-language variation. Each dot is an average over the sample, not a single sentence.")
