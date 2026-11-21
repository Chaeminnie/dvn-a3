"""Tab 0: Overview. Owner: Advait.

How big is the gap? One heatmap of tokens vs English for every language on every tokenizer.
KPIs use the WHOLE dataset (they ignore the sidebar filters); the heatmap follows the filters.
"""
import textwrap

import numpy as np
import plotly.graph_objects as go

import data
import style

# Colour runs on a log scale so 1.5x and 17x are both readable.
LOG_MAX = np.log10(20)


def _heatmap(prem, gini, languages, focus, tokenizer):
    df = data.dedupe(prem)  # Qwen 3 = Qwen 2.5 and Gemini 3.8 Flash = Gemma 3, so show each pair once
    df = df[df["language"].isin(languages)]

    # Columns: fairest tokenizer (lowest Gini across languages) on the left.
    tok_order = (gini[~gini["tokenizer_id"].isin(data.IDENTICAL)]
                 .sort_values("gini")["tokenizer_id"].tolist())
    labels = df.drop_duplicates("tokenizer_id").set_index("tokenizer_id")["tokenizer"]
    tok_order = [t for t in tok_order if t in labels.index]
    # Rows: most expensive language (mean over tokenizers) at the top, English at the bottom.
    lang_order = df.groupby("language")["premium_vs_en"].mean().sort_values(ascending=False).index.tolist()

    grid = df.pivot(index="language", columns="tokenizer_id", values="premium_vs_en").loc[lang_order, tok_order]
    # Wrap long names onto 2-3 lines so they fit above narrow columns at 1366 px.
    x = ["<br>".join(textwrap.wrap(labels[t], 10)) for t in tok_order]
    y = lang_order

    n = len(style.SEQ) - 1
    fig = go.Figure(go.Heatmap(
        z=np.log10(grid.values), x=x, y=y,
        zmin=0, zmax=LOG_MAX,
        colorscale=[[i / n, c] for i, c in enumerate(style.SEQ)],
        customdata=grid.values,
        hovertemplate="%{y} on %{x}: %{customdata:.2f}× the tokens of English<extra></extra>",
        xgap=2, ygap=2,
        colorbar=dict(title=dict(text="Tokens vs<br>English (×)", font=dict(size=12, color=style.MUTED)),
                      tickvals=np.log10([1, 2, 5, 10, 20]), ticktext=["1×", "2×", "5×", "10×", "20×"],
                      tickfont=dict(size=12, color=style.MUTED), thickness=12, outlinewidth=0),
    ))
    # Print the value in every cell (readable without hovering); white text on dark cells.
    for i, lang in enumerate(y):
        for j, tok in enumerate(x):
            v = grid.iat[i, j]
            dark = np.log10(v) / LOG_MAX > 0.55
            fig.add_annotation(x=tok, y=lang, text=style.fmt_x(v), showarrow=False,
                               font=dict(size=12, color="#ffffff" if dark else style.INK))

    # Orange outline on the focus language row, blue outline on the selected tokenizer column.
    if focus in y:
        r = y.index(focus)
        fig.add_shape(type="rect", x0=-0.5, x1=len(x) - 0.5, y0=r - 0.5, y1=r + 0.5,
                      line=dict(color=style.FOCUS, width=3))
    sel = data.IDENTICAL.get(tokenizer, tokenizer)
    if sel in tok_order:
        c = tok_order.index(sel)
        fig.add_shape(type="rect", x0=c - 0.5, x1=c + 0.5, y0=-0.5, y1=len(y) - 0.5,
                      line=dict(color=style.SELECTED, width=3))

    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(side="top", tickangle=0, tickfont=dict(size=12))
    style.plotly_theme(fig, x_title="Tokenizer (fairest on the left)", y_title="Language",
                       height=max(280, 34 * len(y) + 140))
    return fig


def render(state):
    d = state.d
    prem, gini = d["prem"], d["gini"]
    h = data.headline(prem, gini)
    others = prem[prem["lang_code"] != data.ENGLISH]
    lo, hi = others["premium_vs_en"].min(), others["premium_vs_en"].max()

    style.section(
        "How big is the gap?",
        f"The same {h['n_sents']} sentences need {style.fmt_x(lo)} to {style.fmt_x(hi)} the tokens of English, "
        f"depending on language and tokenizer. {h['swing_lang']} alone ranges from "
        f"{style.fmt_x(h['swing_lo'])} to {style.fmt_x(h['swing_hi'])}.",
    )

    # Whole-dataset numbers (not affected by the sidebar filters).
    w, f = h["worst"], h["fairest"]
    # Qwen 3 / Gemini 3.8 Flash are shown under their twin (same counts), so name the kept one.
    kept = data.IDENTICAL.get(f["tokenizer_id"], f["tokenizer_id"])
    twin = next((dup for dup, k in data.IDENTICAL.items() if k == kept), None)
    f_name = data.TOKENIZER[kept]
    f_note = f" {data.TOKENIZER[twin]} gives identical counts." if twin else ""
    style.kpi_row([
        (f"Worst case · {w['language']} on {w['tokenizer']}", style.fmt_x(w["premium_vs_en"]),
         "Highest tokens-vs-English value in the whole dataset."),
        ("Pairs above their byte size", style.fmt_pct(h["share_above"]),
         f"Share of the {h['n_pairs']} language × tokenizer pairs whose token premium is higher than their UTF-8 byte premium, "
         "i.e. the tokenizer adds cost beyond the size of the text."),
        (f"Fairest tokenizer · {f_name}", f"Gini {f['gini']:.2f}",
         "Inequality across the 15 languages: 0 = every language costs the same as English." + f_note),
    ])

    style.chart_title(
        "Tokens vs English, every language on every tokenizer",
        "One cell = total tokens for the language ÷ total tokens for English, same 200 sentences, same tokenizer "
        "(English = 1.0×). Most expensive language at the top, fairest tokenizer on the left.",
    )
    if not state.languages:
        style.empty_state()
    else:
        style.plotly_chart(_heatmap(prem, gini, state.languages, state.focus, state.tokenizer))
        st_note = (f"Orange outline: focus language ({state.focus}). "
                   f"Blue outline: selected tokenizer ({data.TOKENIZER[state.tokenizer]}).")
        style._html(f"<p style='font-size:13px;color:{style.MUTED};margin:-.4rem 0 .6rem'>{st_note}</p>")

    style.how_to_read(
        "- **One cell** compares the same 200 FLORES+ sentences: total tokens in that language divided by total "
        "tokens in English, on the same tokenizer. **1.0×** means it costs the same as English; **3.0×** means "
        "three times the tokens, so three times the input cost at the same per-token price.\n"
        "- **Darker blue = more expensive.** The colour uses a log scale so that 2× and 17× both stand out.\n"
        "- **Read across a row** to see how much one language's cost depends on the tokenizer. "
        "**Read down a column** to see how fair one tokenizer is.\n"
        "- Columns are sorted by Gini (0 = every language costs the same), fairest on the left.\n"
        "- The sidebar **script groups** hide rows; the **focus language** and **tokenizer** are outlined. "
        "The three cards above always use all languages and tokenizers.\n"
        "- Qwen 3 gives the same counts as Qwen 2.5, and Gemini 3.8 Flash the same as Gemma 3, "
        "so each pair is shown as one column."
    )
    style.not_shown(
        "Money. This is a token ratio; what it costs depends on each model's price (see *Absorb, adjust or switch?*).",
        "Why a tokenizer is unfair (training data, vocabulary size). The data shows how big the gap is, not its cause.",
        "Real user text. FLORES+ is translated news-style text; chat messages, code or mixed-language text may tokenize differently.",
        "Output tokens. Only the input text is counted.",
        "Languages outside these 15. The ranking could change with a different set.",
    )
