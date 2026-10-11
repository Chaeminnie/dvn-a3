"""Step 2/3: Count tokens per sentence for each language x tokenizer.

Input:  data/source/flores_sample.csv (lang_code, sent_id, text)
Output: data/processed/token_counts_long.csv
        columns: lang_code, sent_id, tokenizer_id, n_tokens, n_chars, n_bytes

Rules (document these in the data dictionary):
  - Text is normalised with Unicode NFC before counting.
  - Special tokens (BOS/EOS) are NOT counted.
  - A round-trip check (decode(encode(text)) == text) is run for every sentence.
  - Tokenizers that cannot be loaded (e.g. gated, not yet approved) are skipped.
Tokenizers are defined in scripts/tokenizer_config.py.
"""
from pathlib import Path
import unicodedata

import pandas as pd
import tiktoken

from tokenizer_config import TIKTOKEN, HF, HF_KWARGS, load_hf_tokenizer

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "source" / "flores_sample.csv"
OUT = ROOT / "data" / "processed" / "token_counts_long.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(SRC)
df["text"] = df["text"].map(lambda s: unicodedata.normalize("NFC", s))

rows = []
roundtrip_failures = []


def add_rows(tok_id, encode, decode):
    for r in df.itertuples(index=False):
        ids = encode(r.text)
        if decode(ids) != r.text:
            roundtrip_failures.append((tok_id, r.lang_code, r.sent_id))
        rows.append({
            "lang_code": r.lang_code,
            "sent_id": r.sent_id,
            "tokenizer_id": tok_id,
            "n_tokens": len(ids),
            "n_chars": len(r.text),
            "n_bytes": len(r.text.encode("utf-8")),
        })


for tok_id, (enc_name, _, _) in TIKTOKEN.items():
    enc = tiktoken.get_encoding(enc_name)
    add_rows(tok_id, enc.encode_ordinary, enc.decode)  # no special tokens
    print(f"[ok] {tok_id}")

for tok_id, (repo, _, _) in HF.items():
    try:
        tok = load_hf_tokenizer(tok_id)
    except Exception as e:  # gated, missing, or network error
        print(f"[skipped] {tok_id} ({repo}): {type(e).__name__}: {str(e)[:150]}")
        continue
    add_rows(
        tok_id,
        lambda t, tok=tok: tok.encode(t, add_special_tokens=False),
        lambda ids, tok=tok: tok.decode(ids, clean_up_tokenization_spaces=False),
    )
    extra = HF_KWARGS.get(tok_id)
    print(f"[ok] {tok_id} ({repo}){' extra args: ' + str(extra) if extra else ''}")

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

print(f"Wrote {len(out)} rows to {OUT}")
print(f"Round-trip failures: {len(roundtrip_failures)}")
if roundtrip_failures:
    print("First failures:", roundtrip_failures[:5])

preview = out.pivot_table(index="lang_code", columns="tokenizer_id",
                          values="n_tokens", aggfunc="mean").round(1)
print(preview.to_string())