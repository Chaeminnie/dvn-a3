"""Step 5: Check that the 200-sentence sample represents the full devtest.

Recomputes the premium vs English on all 1012 devtest sentences (local files,
git-ignored) and compares it with the premium from the committed sample.

Pass rule (fixed BEFORE running): for every language x tokenizer pair, the relative
difference between sample premium and full premium is at most 5%.

Input:  data/source/flores_full/<lang_code>.csv   (id, text)
        data/processed/token_premium.csv          (sample result)
Output: data/processed/sample_vs_full_check.csv
Tokenizers are defined in scripts/tokenizer_config.py.
"""
from pathlib import Path
import unicodedata

import pandas as pd
import tiktoken

from tokenizer_config import TIKTOKEN, HF, load_hf_tokenizer

ROOT = Path(__file__).resolve().parent.parent
FULL_DIR = ROOT / "data" / "source" / "flores_full"
SAMPLE_PREM = ROOT / "data" / "processed" / "token_premium.csv"
OUT = ROOT / "data" / "processed" / "sample_vs_full_check.csv"
THRESHOLD = 0.05  # max allowed relative difference
BASE_LANG = "eng_Latn"

sample = pd.read_csv(SAMPLE_PREM)
lang_codes = sorted(sample["lang_code"].unique())
in_sample = set(sample["tokenizer_id"].unique())

texts = {}
for code in lang_codes:
    df = pd.read_csv(FULL_DIR / f"{code}.csv").sort_values("id")
    texts[code] = [unicodedata.normalize("NFC", t) for t in df["text"]]
n_full = {len(v) for v in texts.values()}
assert n_full == {1012}, f"Unexpected sentence counts: {n_full}"

encoders = {}
for tok_id, (enc_name, _, _) in TIKTOKEN.items():
    if tok_id in in_sample:
        encoders[tok_id] = tiktoken.get_encoding(enc_name).encode_ordinary
for tok_id in HF:
    if tok_id not in in_sample:
        print(f"[not in sample result, skipped] {tok_id}")
        continue
    tok = load_hf_tokenizer(tok_id)
    encoders[tok_id] = lambda t, tok=tok: tok.encode(t, add_special_tokens=False)

totals = {}
for tok_id, encode in encoders.items():
    for code in lang_codes:
        totals[(code, tok_id)] = sum(len(encode(t)) for t in texts[code])

rows = []
for (code, tok_id), total in totals.items():
    full_prem = total / totals[(BASE_LANG, tok_id)]
    s = sample[(sample["lang_code"] == code) & (sample["tokenizer_id"] == tok_id)]
    sample_prem = float(s["premium_vs_en"].iloc[0])
    rows.append({
        "lang_code": code,
        "tokenizer_id": tok_id,
        "premium_sample": round(sample_prem, 4),
        "premium_full": round(full_prem, 4),
        "rel_diff": round(abs(sample_prem - full_prem) / full_prem, 4),
    })

res = pd.DataFrame(rows).sort_values("rel_diff", ascending=False)
res.to_csv(OUT, index=False)

max_diff = res["rel_diff"].max()
print(f"Wrote {OUT.name} ({len(res)} rows)")
print(f"Max relative difference: {max_diff:.2%} (threshold {THRESHOLD:.0%})")
print("PASS" if max_diff <= THRESHOLD else "FAIL")
print("\nLargest differences:")
print(res.head(8).to_string(index=False))