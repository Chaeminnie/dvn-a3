"""Step 4: Aggregate token counts into premiums and Gini coefficients.

Input:  data/processed/token_counts_long.csv
Output: data/processed/token_premium.csv   (language x tokenizer)
        data/processed/tokenizer_gini.csv  (one row per tokenizer)

Definitions (document these in the data dictionary):
  premium_vs_en       = total tokens in language / total tokens in English, same tokenizer
  byte_premium_vs_en  = total UTF-8 bytes in language / total UTF-8 bytes in English
                        (independent of the tokenizer: the encoding-only baseline)
  premium_over_byte   = premium_vs_en / byte_premium_vs_en
  gini                = Gini coefficient of premium_vs_en across the languages in the file
                        (0 = every language costs the same, 1 = extreme inequality).
                        Gini is scale-invariant, so it equals the Gini of raw token cost.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "data" / "processed" / "token_counts_long.csv"
OUT_PREM = ROOT / "data" / "processed" / "token_premium.csv"
OUT_GINI = ROOT / "data" / "processed" / "tokenizer_gini.csv"
BASE_LANG = "eng_Latn"

df = pd.read_csv(IN)

# Sanity check 1: every language x tokenizer pair covers the same number of sentences.
per_pair = df.groupby(["tokenizer_id", "lang_code"])["sent_id"].nunique()
assert per_pair.nunique() == 1, f"Unequal sentence counts:\n{per_pair[per_pair != per_pair.max()]}"

agg = df.groupby(["lang_code", "tokenizer_id"], as_index=False).agg(
    n_sentences=("sent_id", "nunique"),
    total_tokens=("n_tokens", "sum"),
    total_chars=("n_chars", "sum"),
    total_bytes=("n_bytes", "sum"),
)
agg["mean_tokens_per_sentence"] = agg["total_tokens"] / agg["n_sentences"]

# Premium relative to English, computed within each tokenizer.
en = agg[agg["lang_code"] == BASE_LANG].set_index("tokenizer_id")
agg["premium_vs_en"] = agg["total_tokens"] / agg["tokenizer_id"].map(en["total_tokens"])

# Byte premium: the baseline caused by the encoding alone. Bytes do not depend on the tokenizer.
assert en["total_bytes"].nunique() == 1, "English byte total differs between tokenizers"
agg["byte_premium_vs_en"] = agg["total_bytes"] / en["total_bytes"].iloc[0]
agg["premium_over_byte"] = agg["premium_vs_en"] / agg["byte_premium_vs_en"]

# Sanity check 2: English must be exactly 1.0 for every tokenizer.
eng_check = agg[agg["lang_code"] == BASE_LANG]["premium_vs_en"]
assert np.allclose(eng_check, 1.0), "English premium is not 1.0"

agg = agg.sort_values(["tokenizer_id", "premium_vs_en"], ascending=[True, False])
agg.round(4).to_csv(OUT_PREM, index=False)


def gini(values):
    x = np.sort(np.asarray(values, dtype=float))
    n = len(x)
    idx = np.arange(1, n + 1)
    return (2 * np.sum(idx * x)) / (n * np.sum(x)) - (n + 1) / n


# Byte-level inequality is the same for every tokenizer; report it as a reference line.
byte_by_lang = agg.drop_duplicates("lang_code").set_index("lang_code")["byte_premium_vs_en"]
byte_gini = gini(byte_by_lang.values)

gini_rows = []
for tok_id, g in agg.groupby("tokenizer_id"):
    gini_rows.append({
        "tokenizer_id": tok_id,
        "n_languages": g["lang_code"].nunique(),
        "gini": gini(g["premium_vs_en"].values),
        "gini_byte_baseline": byte_gini,
        "max_premium": g["premium_vs_en"].max(),
        "max_premium_lang": g.loc[g["premium_vs_en"].idxmax(), "lang_code"],
        "median_premium": g["premium_vs_en"].median(),
    })
pd.DataFrame(gini_rows).round(4).to_csv(OUT_GINI, index=False)

print(f"Wrote {OUT_PREM.name} ({len(agg)} rows) and {OUT_GINI.name} ({len(gini_rows)} rows)")
print("\nPremium vs English (x):")
print(agg.pivot_table(index="lang_code", columns="tokenizer_id",
                      values="premium_vs_en").round(2).to_string())
print("\nByte premium vs English (x), same for every tokenizer:")
print(byte_by_lang.round(2).sort_values(ascending=False).to_string())
print("\nGini by tokenizer:")
print(pd.DataFrame(gini_rows).round(3).to_string(index=False))