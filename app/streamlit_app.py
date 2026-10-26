"""Token premium dashboard (DVN A3, data-pipeline view).

Run from the repo root:
    streamlit run app/streamlit_app.py

Reads only the committed CSVs in data/source and data/processed.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "source"
PROC = ROOT / "data" / "processed"
HERE = Path(__file__).resolve().parent

st.set_page_config(page_title="Token premium", page_icon="◐", layout="wide")
st.markdown(f"<style>{(HERE / 'style.css').read_text()}</style>", unsafe_allow_html=True)

# ---------------------------------------------------------------- constants
LABEL = {
    "gpt2": "GPT-2", "cl100k_base": "GPT-4 (cl100k)", "o200k_base": "GPT-4o (o200k)",
    "qwen2.5": "Qwen 2.5", "qwen3": "Qwen 3", "gemma2": "Gemma 2", "gemma3": "Gemma 3",
    "llama3": "Llama 3.2", "mistral_nemo": "Mistral Nemo",
    "claude_haiku_4_5": "Claude Haiku 4.5", "claude_sonnet_5_5": "Claude Sonnet 5.5",
    "gemini_3_8_flash": "Gemini 3.8 Flash",
}
# Validated categorical palette (light). Family -> colour.
FAMCOL = {"gpt": "#2a78d6", "gemma": "#eb6834", "qwen": "#1baf7a", "claude": "#eda100",
          "llama": "#e87ba4", "mistral": "#008300", "gemini": "#6250d6"}
FAMNAME = {"gpt": "GPT", "gemma": "Gemma", "qwen": "Qwen", "claude": "Claude",
           "llama": "Llama", "mistral": "Mistral", "gemini": "Gemini"}
INK, FOREST, NEON = "#0b0f0e", "#0b4a43", "#19ee6b"
HEAT_BINS = [1.25, 1.5, 2, 3, 5, 8]
HEAT_COLS = ["#eef5f3", "#cfe4df", "#9fcac2", "#5fa59b", "#2a766c", "#0b4a43", "#052b27"]
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"
ALIASES = {"en": "eng_Latn", "fr": "fra_Latn", "de": "deu_Latn", "es": "spa_Latn", "ru": "rus_Cyrl",
           "ar": "arb_Arab", "hi": "hin_Deva", "ta": "tam_Taml", "sw": "swh_Latn", "ko": "kor_Hang",
           "zh": "cmn_Hans", "ja": "jpn_Jpan", "th": "tha_Thai", "my": "mya_Mymr", "am": "amh_Ethi",
           "chinese": "cmn_Hans", "mandarin": "cmn_Hans", "arabic": "arb_Arab", "burmese": "mya_Mymr",
           "myanmar": "mya_Mymr", "farsi": "pes_Arab"}


import inspect

def _fit(fn):
    """Full-width kwarg that works on old and new Streamlit."""
    return {"width": "stretch"} if "width" in inspect.signature(fn).parameters else {"use_container_width": True}


FIT_CHART, FIT_DF, FIT_ED = _fit(st.plotly_chart), _fit(st.dataframe), _fit(st.data_editor)


# ---------------------------------------------------------------- data
def _mtime() -> float:
    files = list(SRC.glob("*.csv")) + list(PROC.glob("*.csv"))
    return max(f.stat().st_mtime for f in files)


@st.cache_data
def load(_stamp: float):
    prem = pd.read_csv(PROC / "token_premium.csv")
    gini = pd.read_csv(PROC / "tokenizer_gini.csv").set_index("tokenizer_id")
    tok = pd.read_csv(SRC / "tokenizers.csv", parse_dates=["release_date"])
    lang = pd.read_csv(SRC / "lang_meta.csv")
    price = pd.read_csv(SRC / "prices.csv")
    mix = pd.read_csv(SRC / "language_mix.csv")
    return prem, gini, tok, lang, price, mix


prem, gini, tok, lang, price, mix0 = load(_mtime())
tok = tok[tok.tokenizer_id.isin(prem.tokenizer_id.unique())].sort_values("release_date").reset_index(drop=True)
TIDS = list(tok.tokenizer_id)
FAM = dict(zip(tok.tokenizer_id, tok.family))
DATE = dict(zip(tok.tokenizer_id, tok.release_date))
LNAME = dict(zip(lang.lang_code, lang.language))
LCODES = list(lang.lang_code)
P = prem.set_index(["tokenizer_id", "lang_code"])


def lab(t: str) -> str:
    return LABEL.get(t, t)


def premium(t: str, l: str) -> float:
    return float(P.loc[(t, l), "premium_vs_en"])


def tokens_per_sentence(t: str, l: str) -> float:
    return float(P.loc[(t, l), "mean_tokens_per_sentence"])


def list_price(t: str):
    """(input, output) USD per 1M tokens valid today, or (None, None)."""
    today = pd.Timestamp(date.today())
    rows = price[(price.tokenizer_id == t) & (price.source_tier == "official")]
    for r in rows.itertuples():
        a = pd.to_datetime(r.valid_from) if pd.notna(r.valid_from) else pd.Timestamp.min
        b = pd.to_datetime(r.valid_until) if pd.notna(r.valid_until) else pd.Timestamp.max
        if a <= today <= b:
            return float(r.input_usd_per_1m), float(r.output_usd_per_1m)
    return None, None


# ---------------------------------------------------------------- state
ss = st.session_state
if "mau" not in ss:
    EQUAL = round(100 / len(LCODES), 2)
    for _c in LCODES:
        ss[f"share_{_c}"] = EQUAL
    ss.mix = pd.DataFrame({"code": LCODES, "Share (%)": [EQUAL] * len(LCODES)})
    ss.mau = 100_000
    ss.prices = {}
    ss.upload_msg = ""
    ss.up_id = None

# Streamlit forgets the value of any widget that is not drawn in a run. Because only
# one view is drawn at a time, copy every stored value back so nothing is lost.
for _k in list(ss.keys()):
    if _k not in ("view", "up_id", "upload_msg", "prices", "mix", "upl"):
        try:
            ss[_k] = ss[_k]
        except Exception:
            pass

def _reset_mix():
    for c in LCODES:
        ss[f"share_{c}"] = round(100 / len(LCODES), 2)
    ss.upload_msg = ""


# ---------------------------------------------------------------- header
st.markdown('<div class="eyebrow">DVN · Data narrative · Pricing & monetisation view</div>', unsafe_allow_html=True)
st.markdown('<div class="hero">Same sentence, different bill.</div>', unsafe_allow_html=True)
st.markdown('<p class="lede">The same sentence costs more tokens in some languages than in English. '
            'This page shows how much more, what your language mix would pay, and whether newer '
            'tokenizers are closing the gap.</p>', unsafe_allow_html=True)

VIEWS = ["Cost vs English", "My language mix", "Is it shrinking?"]
if "view" not in ss:
    ss["view"] = VIEWS[0]
with st.container(key="viewnav"):
    view = st.radio("View", VIEWS, horizontal=True, key="view", label_visibility="collapsed")

# ================================================================ TAB 1
if view == VIEWS[0]:
    st.markdown('<div class="sec">Where the gap comes from</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 2, 1])
    t1 = c1.selectbox("Tokenizer", TIDS, index=TIDS.index("gpt2") if "gpt2" in TIDS else 0,
                      format_func=lab, key="t1")
    mode = c2.radio("Show", ["Premium vs English (×)", "Tokens per sentence"], horizontal=True, key="mode1")
    logx = c3.checkbox("Log scale", value=False, key="log1", disabled=mode != "Premium vs English (×)")

    g = gini.loc[t1]
    sub = prem[prem.tokenizer_id == t1]
    st.markdown(
        f'<div class="tiles">'
        f'<div class="tile dark"><div class="n">{g.gini:.2f}</div><div class="l">Gini across languages</div>'
        f'<div class="s">0 = every language pays the same. Byte baseline: {g.gini_byte_baseline:.2f}</div></div>'
        f'<div class="tile neon"><div class="n">{g.max_premium:.1f}×</div><div class="l">Worst language</div>'
        f'<div class="s">{LNAME.get(g.max_premium_lang, g.max_premium_lang)}</div></div>'
        f'<div class="tile"><div class="n">{g.median_premium:.1f}×</div><div class="l">Median language</div>'
        f'<div class="s">of {int(g.n_languages)} languages vs English</div></div></div>',
        unsafe_allow_html=True)

    if mode.startswith("Premium"):
        d = sub.sort_values("premium_vs_en")
        names = [LNAME.get(c, c) for c in d.lang_code]
        fig = go.Figure()
        fig.add_bar(y=names, x=d.premium_vs_en, orientation="h", marker_color=FOREST, name="Token premium",
                    hovertemplate="%{y}<br>%{x:.2f}× English tokens<extra></extra>")
        fig.add_scatter(y=names, x=d.byte_premium_vs_en, mode="markers", name="Byte baseline",
                        marker=dict(symbol="diamond", size=11, color=NEON, line=dict(color=INK, width=1.5)),
                        hovertemplate="%{y}<br>%{x:.2f}× English bytes (UTF-8)<extra></extra>")
        fig.update_xaxes(title="× English (1 = same as English)", type="log" if logx else "linear",
                         gridcolor="#e6e9ec", zeroline=False)
    else:
        d = sub.sort_values("mean_tokens_per_sentence")
        names = [LNAME.get(c, c) for c in d.lang_code]
        fig = go.Figure()
        fig.add_bar(y=names, x=d.mean_tokens_per_sentence, orientation="h", marker_color=FOREST,
                    name="Tokens per sentence",
                    hovertemplate="%{y}<br>%{x:.1f} tokens per sentence<extra></extra>")
        fig.update_xaxes(title="Mean tokens per sentence", gridcolor="#e6e9ec")
    fig.update_layout(height=520, margin=dict(l=10, r=20, t=10, b=10), paper_bgcolor="#fff", plot_bgcolor="#fff",
                      font=dict(family=FONT, color=INK, size=13), legend=dict(orientation="h", y=1.07, x=0),
                      yaxis=dict(automargin=True))
    st.plotly_chart(fig, **FIT_CHART, config={"displayModeBar": False})

    worst = d.iloc[-1]
    below = (sub.premium_vs_en < sub.byte_premium_vs_en).sum()
    st.markdown(
        f'<p class="story">With {lab(t1)}, {LNAME.get(worst.lang_code)} needs '
        f'{worst.premium_vs_en:.1f}× the tokens of English; {int(below)} of {len(sub)} languages '
        f'cost less than their raw UTF-8 byte ratio.</p>', unsafe_allow_html=True)

    with st.expander("What is the byte baseline?"):
        st.write("A character in Burmese takes 3 bytes in UTF-8, one in English takes 1. So even a tokenizer "
                 "that just splits text into bytes would see Burmese as longer. The diamond marks that ratio. "
                 "It is a reference line, not a limit: a tokenizer with a good vocabulary can land below it "
                 "(bar shorter than the diamond), and a poorly fitted one lands far above it.")

    st.markdown('<div class="sec">All tokenizers at a glance</div>', unsafe_allow_html=True)
    piv = prem.pivot(index="lang_code", columns="tokenizer_id", values="premium_vs_en")[TIDS]
    piv = piv.loc[piv.mean(axis=1).sort_values().index]
    z = piv.apply(lambda col: col.map(lambda v: sum(v >= b for b in HEAT_BINS)))
    cs = []
    for i, c in enumerate(HEAT_COLS):
        cs += [[i / 7, c], [(i + 1) / 7, c]]
    hm = go.Figure(go.Heatmap(
        z=z.values, x=[lab(t) for t in piv.columns], y=[LNAME.get(c, c) for c in piv.index],
        colorscale=cs, zmin=0, zmax=6.999, showscale=False, xgap=2, ygap=2,
        text=[[f"{v:.1f}×" for v in row] for row in piv.values], texttemplate="%{text}",
        textfont=dict(size=11), customdata=piv.values,
        hovertemplate="%{y} · %{x}<br>%{customdata:.2f}× English tokens<extra></extra>"))
    hm.update_layout(height=520, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#fff", plot_bgcolor="#fff",
                     font=dict(family=FONT, color=INK, size=12), xaxis=dict(side="top", tickangle=-30),
                     yaxis=dict(automargin=True))
    st.plotly_chart(hm, **FIT_CHART, config={"displayModeBar": False})
    st.caption("Colour steps: <1.25× · 1.25–1.5× · 1.5–2× · 2–3× · 3–5× · 5–8× · ≥8×. Sorted by average premium. "
               "Qwen 2.5 = Qwen 3 and Gemma 3 = Gemini 3.8 Flash give identical counts, so they are not independent. "
               "Claude Sonnet 5.5 counts about 33–46% more tokens than Haiku 4.5 on Latin-script text, "
               "which makes its ratios look lower for other scripts.")

# ================================================================ TAB 2
if view == VIEWS[1]:
    st.markdown('<div class="sec">What your mix costs</div>', unsafe_allow_html=True)
    st.markdown('<p class="lede">Tell us who your users are and what a typical request looks like. '
                'We apply each tokenizer\'s premium to your mix.</p>', unsafe_allow_html=True)

    left, right = st.columns([1, 1], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("**1. Your language mix**")
            st.caption("Default is equal weights, a placeholder rather than real usage data. "
                       "Type a share for each language, or upload your own numbers.")
            st.button("Reset to equal weights", on_click=_reset_mix)
            up = st.file_uploader("Upload your own mix (CSV: language, users or share)", type=["csv"], key="upl")
            if up is not None and ss.up_id != (up.name, up.size):
                ss.up_id = (up.name, up.size)
                try:
                    df = pd.read_csv(up)
                    lcol = next((c for c in df.columns if re.search("lang", str(c), re.I)), df.columns[0])
                    vcol = next((c for c in df.columns if c != lcol and pd.api.types.is_numeric_dtype(df[c])), None)
                    if vcol is None:
                        raise ValueError("no numeric column found")
                    lookup = {}
                    for r in lang.itertuples():
                        lookup[r.lang_code.lower()] = r.lang_code
                        lookup[r.iso_639_3.lower()] = r.lang_code
                        lookup[r.language.lower()] = r.lang_code
                        lookup[r.language.lower().split(" (")[0]] = r.lang_code
                    lookup.update({k: v for k, v in ALIASES.items() if v in LCODES})
                    new = {c: 0.0 for c in LCODES}
                    miss = []
                    for name, val in zip(df[lcol].astype(str), df[vcol]):
                        key = name.strip().lower()
                        code = lookup.get(key) or lookup.get(key.replace("-", "_"))
                        if code and pd.notna(val):
                            new[code] += float(val)
                        else:
                            miss.append(name)
                    s = sum(new.values())
                    if s <= 0:
                        raise ValueError("no language matched")
                    if s > 100.5:  # counts, not shares
                        ss.mau = int(round(s)); ss["mau_in"] = ss.mau
                    for c in LCODES:
                        ss[f"share_{c}"] = round(100 * new[c] / s, 2)
                    ss.upload_msg = ("Loaded. " + (f"Not matched (ignored): {', '.join(miss)}." if miss else "All rows matched.")
                                     + (" Total users used as MAU." if s > 100.5 else ""))
                except Exception as e:  # noqa: BLE001
                    ss.upload_msg = f"Could not read that file: {e}"
            if ss.upload_msg:
                st.caption(ss.upload_msg)
            # Plain number inputs: type a value, press Enter, it sticks.
            cols = st.columns(3)
            for i, c in enumerate(LCODES):
                cols[i % 3].number_input(LNAME[c].split(" (")[0], min_value=0.0, step=1.0, format="%.2f", key=f"share_{c}")
            ss.mix = pd.DataFrame({"code": LCODES, "Share (%)": [float(ss[f"share_{c}"]) for c in LCODES]})
            total = float(ss.mix["Share (%)"].sum())
            st.caption(f"Shares add up to {total:.1f}%. They are rescaled to 100% for the maths.")

    with right:
        with st.container(border=True):
            st.markdown("**2. Your service**")
            a, b = st.columns(2)
            ss.mau = a.number_input("Monthly active users", min_value=0, value=int(ss.mau), step=10_000, key="mau_in")
            rpu = b.number_input("Requests per user per month", min_value=1, value=200, step=10, key="rpu")
            a, b = st.columns(2)
            en_in = a.number_input("English input tokens / request", min_value=1, value=500, step=50, key="en_in")
            en_out = b.number_input("English output tokens / request", min_value=0, value=300, step=50, key="en_out")
            quota = st.number_input("Token quota per user per month (optional)", min_value=0, value=200_000,
                                    step=10_000, key="quota", help="Used to count users who would run out. 0 turns it off.")
            st.caption("Assumption: output length grows by the same premium as input.")
        with st.container(border=True):
            st.markdown("**3. Tokenizer and price**")
            t2 = st.selectbox("Tokenizer", TIDS, index=TIDS.index("claude_sonnet_5_5") if "claude_sonnet_5_5" in TIDS else 0,
                              format_func=lab, key="t2")
            li, lo = list_price(t2)
            saved = ss.prices.get(t2, (li, lo))
            a, b = st.columns(2)
            pin = a.number_input("Input $ / 1M tokens", min_value=0.0, value=saved[0], step=0.25,
                                 placeholder="no list price", key=f"pin_{t2}")
            pout = b.number_input("Output $ / 1M tokens", min_value=0.0, value=saved[1], step=0.25,
                                  placeholder="same as input", key=f"pout_{t2}")
            ss.prices[t2] = (pin, pout)
            if li is None:
                st.caption("No list price for this tokenizer (open model). Type your own price to see costs.")
            else:
                st.caption("List price from data/source/prices.csv. Edit to test other prices.")

    # ----- calculation
    tot = float(ss.mix["Share (%)"].sum())
    if tot <= 0:
        st.warning("All shares are 0. Add at least one language.")
        st.stop()
    shares = dict(zip(ss.mix.code, ss.mix["Share (%)"] / tot))

    def run(t: str, pin_, pout_):
        rows = []
        for c in LCODES:
            sh = shares[c]
            if sh <= 0:
                continue
            p = premium(t, c)
            tin, tout = en_in * p, en_out * p
            ttl = tin + tout
            cost = float('nan')
            if pin_ is not None:
                po = pout_ if pout_ is not None else pin_
                cost = (tin * pin_ + tout * po) / 1e6
            rows.append(dict(code=c, share=sh, premium=p, tokens=ttl, cost=cost,
                             req_at_quota=(quota / ttl) if quota else float('nan')))
        return pd.DataFrame(rows)

    R = run(t2, pin, pout)
    bl_prem = float((R.share * R.premium).sum())
    bl_tok = float((R.share * R.tokens).sum())
    bl_cost = float((R.share * R.cost).sum()) if R.cost.notna().all() else None
    bill = bl_cost * ss.mau * rpu if bl_cost is not None else None
    short = None
    if quota:
        short = float(R[R.req_at_quota < rpu].share.sum())
    en_cost = ((en_in * pin + en_out * (pout if pout is not None else pin)) / 1e6) if pin is not None else None

    tiles = (f'<div class="tile dark"><div class="n">{bl_prem:.2f}×</div><div class="l">Your blended premium</div>'
             f'<div class="s">{bl_tok:,.0f} tokens per request on average</div></div>')
    if bill is not None:
        extra = f"{(bl_cost / en_cost - 1) * 100:+.0f}% vs an all-English mix" if en_cost else ""
        tiles += (f'<div class="tile neon"><div class="n">${bill:,.0f}</div><div class="l">Monthly bill</div>'
                  f'<div class="s">{extra}</div></div>')
    else:
        tiles += '<div class="tile"><div class="n">–</div><div class="l">Monthly bill</div><div class="s">Enter a price above</div></div>'
    if short is not None:
        tiles += (f'<div class="tile"><div class="n">{short * 100:.0f}%</div><div class="l">Users who run out</div>'
                  f'<div class="s">of quota before {rpu} requests (about {short * ss.mau:,.0f} users)</div></div>')
    st.markdown(f'<div class="tiles">{tiles}</div>', unsafe_allow_html=True)

    show = pd.DataFrame({
        "Language": R.code.map(lambda c: LNAME.get(c, c)),
        "Share": (R.share * 100).round(1),
        "Premium (×)": R.premium.round(2),
        "Tokens / request": R.tokens.round(0),
        "Cost / request ($)": R.cost.round(5),
        "Requests at quota": R.req_at_quota.round(0),
    }).sort_values("Premium (×)", ascending=False)
    st.dataframe(show, hide_index=True, **FIT_DF,
                 column_config={"Share": st.column_config.NumberColumn(format="%.1f%%")})

    st.markdown('<div class="sec">Compare tokenizers on your mix</div>', unsafe_allow_html=True)
    pick = st.multiselect("Tokenizers", TIDS, default=[t for t in ["gpt2", "o200k_base", "gemma3", "claude_sonnet_5_5"] if t in TIDS],
                          format_func=lab, key="pick2")
    rows = []
    for t in pick:
        pi, po = ss.prices.get(t, list_price(t))
        r = run(t, pi, po)
        blp = float((r.share * r.premium).sum())
        blt = float((r.share * r.tokens).sum())
        blc = float((r.share * r.cost).sum()) if r.cost.notna().all() else None
        rows.append({"Tokenizer": lab(t), "Premium on your mix (×)": round(blp, 2),
                     "Tokens / request": round(blt),
                     "Monthly bill ($)": round(blc * ss.mau * rpu) if blc is not None else None,
                     "Price used (in/out)": f"{pi:g} / {(po if po is not None else pi):g}" if pi is not None else "no list price"})
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, **FIT_DF)
    st.caption("Compare absolute tokens per request, not only ratios: ratios are relative to each tokenizer's own English. "
               "Tokenizers without a list price show no bill until you type a price on their page above.")

# ================================================================ TAB 3
if view == VIEWS[2]:
    st.markdown('<div class="sec">Is the gap closing?</div>', unsafe_allow_html=True)
    METRICS = ["Gini across languages (lower = fairer)", "Median premium vs English",
               "Premium for one language", "Tokens per sentence on my mix"]
    c1, c2 = st.columns([2, 2])
    metric = c1.selectbox("Measure", METRICS, key="metric3")
    lsel = None
    if metric == METRICS[2]:
        lsel = c2.selectbox("Language", [c for c in LCODES if c != "eng_Latn"], format_func=lambda c: LNAME.get(c, c),
                            index=[c for c in LCODES if c != "eng_Latn"].index("mya_Mymr") if "mya_Mymr" in LCODES else 0, key="lang3")

    def value(t: str) -> float:
        if metric == METRICS[0]:
            return float(gini.loc[t, "gini"])
        if metric == METRICS[1]:
            return float(gini.loc[t, "median_premium"])
        if metric == METRICS[2]:
            return premium(t, lsel)
        tot_ = float(ss.mix["Share (%)"].sum()) or 1.0
        return sum(float(s) / tot_ * tokens_per_sentence(t, c)
                   for c, s in zip(ss.mix.code, ss.mix["Share (%)"]))

    d = tok.copy()
    d["v"] = d.tokenizer_id.map(value)
    fig = go.Figure()
    for fam, grp in d.groupby("family", sort=False):
        grp = grp.sort_values("release_date")
        col = FAMCOL.get(fam, "#555")
        fig.add_scatter(x=grp.release_date, y=grp.v, mode="lines+markers+text", name=FAMNAME.get(fam, fam),
                        line=dict(color=col, width=3), marker=dict(size=12, color=col, line=dict(color="#fff", width=2)),
                        text=[lab(t) for t in grp.tokenizer_id], textposition="top center", textfont=dict(size=11),
                        customdata=grp.release_date.dt.strftime("%Y-%m-%d"),
                        hovertemplate="%{text}<br>released %{customdata}<br>%{y:.2f}<extra></extra>")
    fig.update_layout(height=520, margin=dict(l=10, r=20, t=10, b=10), paper_bgcolor="#fff", plot_bgcolor="#fff",
                      font=dict(family=FONT, color=INK, size=13), legend=dict(orientation="h", y=1.08, x=0),
                      xaxis=dict(title="Release date", gridcolor="#e6e9ec"),
                      yaxis=dict(title=metric, gridcolor="#e6e9ec", rangemode="tozero"))
    st.plotly_chart(fig, **FIT_CHART, config={"displayModeBar": False})

    # data-backed reading
    lines = []
    for fam, grp in d.groupby("family", sort=False):
        grp = grp.sort_values("release_date")
        if len(grp) < 2:
            continue
        a, b = grp.iloc[0], grp.iloc[-1]
        ch = (b.v / a.v - 1) * 100 if a.v else 0
        word = "fell" if ch < -1 else ("rose" if ch > 1 else "stayed about the same")
        lines.append(f"- **{FAMNAME.get(fam, fam)}**: {lab(a.tokenizer_id)} → {lab(b.tokenizer_id)} {word} "
                     f"({a.v:.2f} → {b.v:.2f}, {ch:+.0f}%).")
    st.markdown("**Reading the chart**")
    st.markdown("\n".join(lines) if lines else "No family has two or more tokenizers.")
    st.caption("Lines connect tokenizers of the same family only. Different families are different designs, not generations. "
               "Llama and Mistral have one tokenizer each, so they cannot show a trend, and Qwen 2.5 = Qwen 3 is the same tokenizer twice. "
               "The trend rests on a few tokenizers per family, so treat it as a pattern in this sample rather than a law.")

    st.markdown('<div class="sec">Compare two or more</div>', unsafe_allow_html=True)
    sel = st.multiselect("Tokenizers", TIDS, default=[t for t in ["gpt2", "gemma2", "gemma3"] if t in TIDS],
                         format_func=lab, key="cmp")
    if sel:
        cmp = pd.DataFrame({
            "Tokenizer": [lab(t) for t in sel],
            "Released": [DATE[t].strftime("%Y-%m-%d") for t in sel],
            "Gini": [round(float(gini.loc[t, "gini"]), 3) for t in sel],
            "Median premium (×)": [round(float(gini.loc[t, "median_premium"]), 2) for t in sel],
            "Worst language": [LNAME.get(gini.loc[t, "max_premium_lang"]) for t in sel],
            "Worst premium (×)": [round(float(gini.loc[t, "max_premium"]), 2) for t in sel],
            "Measure on chart": [round(value(t), 2) for t in sel],
        })
        st.dataframe(cmp, hide_index=True, **FIT_DF)

st.divider()
st.caption("Data: FLORES+ devtest, 200-sentence sample (sampling error up to about 3%), list prices only, input and output "
           "tokens scaled by the same premium. Language mix is a placeholder until you upload real usage. "
           "Source files: data/source and data/processed.")