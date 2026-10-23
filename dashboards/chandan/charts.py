import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from loaders import FAMILY_TITLES, IDENTICAL, SHORT, dedupe

FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"

# Blue = the tokenizer you picked, orange = the focus language, grey = everything else.
# Both blue/orange pairs pass the colour vision deficiency check (protan, deutan, tritan).
LIGHT = dict(selected="#2a78d6", focus="#eb6834", context="#a9a8a1",
             ink="#0b0b0b", muted="#6f6e69", grid="#e1e0d9", surface="#ffffff")
DARK = dict(selected="#3987e5", focus="#d95926", context="#6b6a65",
            ink="#f0efec", muted="#a8a79f", grid="#2c2c2a", surface="#0e1117")


def _style(fig, c, height):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=16, t=36, b=8),
        font=dict(family=FONT, size=13, color=c["ink"]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(font=dict(family=FONT, size=13)),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0, font=dict(size=12)),
    )
    fig.update_xaxes(gridcolor=c["grid"], zeroline=False, linecolor=c["grid"])
    fig.update_yaxes(gridcolor=c["grid"], zeroline=False, linecolor=c["grid"])
    return fig


def ranking(df, focus, c):
    """A. Token premium per language for one tokenizer, biggest at the top."""
    d = df.sort_values("premium_vs_en")  # Plotly draws horizontal bars bottom-up
    colours = [c["focus"] if lang == focus else c["selected"] for lang in d["language"]]

    fig = go.Figure(go.Bar(
        x=d["premium_vs_en"],
        y=d["language"],
        orientation="h",
        marker=dict(color=colours, cornerradius=4),
        text=[f"{p:.1f}×" for p in d["premium_vs_en"]],
        textposition="outside",
        textfont=dict(color=c["ink"], size=12),
        cliponaxis=False,
        customdata=d[["mean_tokens_per_sentence", "total_tokens"]],
        hovertemplate="<b>%{y}</b><br>%{x:.2f}× English<br>"
                      "%{customdata[0]:.0f} tokens per sentence<br>"
                      "%{customdata[1]:,} tokens in total<extra></extra>",
        showlegend=False,
    ))
    fig.add_vline(x=1, line=dict(color=c["muted"], width=1, dash="dot"))
    fig.add_annotation(x=1, y=1, yref="paper", yanchor="bottom", text="English = 1×",
                       showarrow=False, font=dict(size=11, color=c["muted"]))

    xmax = d["premium_vs_en"].max()
    fig.update_xaxes(title_text="Tokens vs English",
                     range=[0, xmax * 1.15], ticksuffix="×")
    fig.update_yaxes(title_text=None, showgrid=False)
    fig.update_layout(bargap=0.3)
    return _style(fig, c, height=max(260, 28 * len(d) + 90))


def _label_positions(points):
    """Pick a text position per language so neighbouring labels don't sit on each other."""
    pos = {lang: "middle right" for lang in points["language"]}
    pos["English"] = "bottom right"
    # These pairs sit close on the x axis. The higher dot gets its label on top.
    for a, b in [("Arabic", "Amharic"), ("Hindi", "Thai"), ("Tamil", "Burmese")]:
        pa = points[points["language"] == a]
        pb = points[points["language"] == b]
        if pa.empty or pb.empty:
            continue
        a_high = pa["premium_vs_en"].iloc[0] >= pb["premium_vs_en"].iloc[0]
        pos[a] = "top center" if a_high else "bottom center"
        pos[b] = "bottom center" if a_high else "top center"
    return pos


def script_vs_tokenizer(prem, tok_id, tok_name, focus, langs, c):
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
        line=dict(color=c["muted"], width=1.5, dash="dash"),
        name="Script only", hoverinfo="skip",
    ))

    fig.add_trace(go.Scatter(
        x=ctx["byte_premium_vs_en"], y=ctx["premium_vs_en"], mode="markers",
        marker=dict(size=7, color=c["context"], opacity=0.6),
        name="Other tokenizers",
        customdata=ctx[["language", "tokenizer"]],
        hovertemplate="<b>%{customdata[0]}</b> on %{customdata[1]}<br>"
                      "bytes %{x:.2f}× · tokens %{y:.2f}×<extra></extra>",
    ))

    # Label only the languages that stand apart. The cluster near 1× is listed in the caption.
    pos = _label_positions(sel)
    labelled = sel["byte_premium_vs_en"].ge(1.6) | sel["language"].eq("English")
    rest = sel[sel["language"] != focus]
    fig.add_trace(go.Scatter(
        x=rest["byte_premium_vs_en"], y=rest["premium_vs_en"], mode="markers+text",
        marker=dict(size=11, color=c["selected"], line=dict(width=2, color=c["surface"])),
        text=[lang if labelled[i] else "" for i, lang in rest["language"].items()],
        textposition=[pos[lang] for lang in rest["language"]],
        textfont=dict(color=c["ink"], size=12),
        name=tok_name,
        customdata=rest[["language"]],
        hovertemplate="<b>%{customdata[0]}</b><br>bytes %{x:.2f}× · tokens %{y:.2f}×<extra></extra>",
    ))

    f = sel[sel["language"] == focus]
    if not f.empty:
        fig.add_trace(go.Scatter(
            x=f["byte_premium_vs_en"], y=f["premium_vs_en"], mode="markers+text",
            marker=dict(size=15, color=c["focus"], line=dict(width=2, color=c["surface"])),
            text=[f"{focus} {f['premium_vs_en'].iloc[0]:.1f}×"],
            textposition=pos.get(focus, "middle right"),
            textfont=dict(color=c["ink"], size=12),
            name=focus,
            hovertemplate=f"<b>{focus}</b><br>bytes %{{x:.2f}}× · tokens %{{y:.2f}}×<extra></extra>",
        ))

    fig.add_annotation(xref="paper", yref="paper", x=0.01, y=0.99, xanchor="left", yanchor="top",
                       text="Above the line: the tokenizer adds cost",
                       showarrow=False, align="left", font=dict(size=11, color=c["muted"]))

    # Log scales because these are ratios: 2× to 4× is the same step as 4× to 8×.
    # Fixed ranges so switching tokenizer moves the dots instead of the axes.
    ticks_x = [1, 1.5, 2, 3, 4]
    ticks_y = [1, 2, 3, 5, 10, 20]
    fig.update_xaxes(type="log", range=[math.log10(0.85), math.log10(5)],
                     tickvals=ticks_x, ticktext=[f"{t:g}×" for t in ticks_x],
                     title_text="Text size vs English (UTF-8 bytes)")
    fig.update_yaxes(type="log", range=[math.log10(0.85), math.log10(20)],
                     tickvals=ticks_y, ticktext=[f"{t:g}×" for t in ticks_y],
                     title_text="Tokens vs English")
    return _style(fig, c, height=460)


def generations(prem, focus, tok_id, c):
    """C. One small panel per family: does the focus language get cheaper in newer tokenizers?"""
    d = prem[prem["language"] == focus]
    fams = list(FAMILY_TITLES)

    titles = []
    for fam in fams:
        g = d[d["family"] == fam].sort_values("generation_order")
        dp = g["premium_vs_en"].iloc[-1] / g["premium_vs_en"].iloc[0] - 1
        dt = g["total_tokens"].iloc[-1] / g["total_tokens"].iloc[0] - 1
        note = f"{dp:+.0%}"
        # Flag when the ratio moved but the language's own token count did not.
        if abs(dp - dt) > 0.05:
            note += f" (own tokens {dt:+.0%})"
        titles.append(f"<b>{FAMILY_TITLES[fam]}</b>  {note}")

    fig = make_subplots(rows=1, cols=len(fams), shared_yaxes=True,
                        subplot_titles=titles, horizontal_spacing=0.04)

    ymax = d[d["family"].isin(fams)]["premium_vs_en"].max()
    for i, fam in enumerate(fams, start=1):
        g = d[d["family"] == fam].sort_values("generation_order")
        fig.add_trace(go.Scatter(
            x=[SHORT[t] for t in g["tokenizer_id"]],
            y=g["premium_vs_en"],
            mode="lines+markers+text",
            line=dict(color=c["focus"], width=2),
            marker=dict(size=10,
                        color=[c["selected"] if t == tok_id else c["focus"] for t in g["tokenizer_id"]],
                        line=dict(width=2, color=c["surface"])),
            text=[f"{p:.1f}×" for p in g["premium_vs_en"]],
            textposition="top center",
            textfont=dict(color=c["ink"], size=11),
            cliponaxis=False,
            showlegend=False,
            hovertemplate="%{x}: %{y:.2f}× English<extra></extra>",
        ), row=1, col=i)

    fig.update_yaxes(range=[0, ymax * 1.25], ticksuffix="×")
    fig.update_yaxes(title_text="vs English", row=1, col=1)
    fig.update_xaxes(tickfont=dict(size=11), showgrid=False)
    fig.update_annotations(font=dict(size=12, color=c["ink"]))
    _style(fig, c, height=300)
    fig.update_layout(margin=dict(t=40))
    return fig


def fairness(gini, tok_id, c):
    """D. Inequality per tokenizer against the inequality the script alone would give."""
    d = dedupe(gini).sort_values("gini", ascending=False)  # fairest ends up on top
    keep = IDENTICAL.get(tok_id, tok_id)
    colours = [c["selected"] if t == keep else c["context"] for t in d["tokenizer_id"]]
    base = d["gini_byte_baseline"].iloc[0]

    fig = go.Figure(go.Bar(
        x=d["gini"], y=d["tokenizer"], orientation="h",
        marker=dict(color=colours, cornerradius=4),
        text=[f"{g:.2f}" for g in d["gini"]],
        textposition="outside",
        textfont=dict(color=c["ink"], size=12),
        cliponaxis=False,
        customdata=d[["max_premium", "median_premium"]],
        hovertemplate="<b>%{y}</b><br>Gini %{x:.3f}<br>"
                      "worst language %{customdata[0]:.1f}× · median %{customdata[1]:.1f}×<extra></extra>",
        showlegend=False,
    ))
    fig.add_vline(x=base, line=dict(color=c["muted"], width=1.5, dash="dash"))
    fig.add_annotation(x=base, y=1, yref="paper", yanchor="bottom", xanchor="left",
                       text=f" Script only: {base:.2f}", showarrow=False,
                       font=dict(size=11, color=c["muted"]))
    n = int(d["n_languages"].iloc[0])
    fig.update_xaxes(range=[0, 0.52],
                     title_text=f"Gini across {n} languages (0 = all cost the same)")
    fig.update_yaxes(title_text=None, showgrid=False)
    fig.update_layout(bargap=0.3)
    return _style(fig, c, height=380)
