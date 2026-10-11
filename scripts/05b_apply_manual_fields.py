"""Step 5b: Apply hand-curated fields to the tokenizer registry.

Reads data/source/tokenizers_manual.csv and overwrites release_date / source_url
in data/source/tokenizers.csv (rows with an empty manual value keep their current value).
Adds a date_basis column. Safe to re-run; run it right after 05.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "data" / "source" / "tokenizers.csv"
MANUAL = ROOT / "data" / "source" / "tokenizers_manual.csv"

reg = pd.read_csv(REG, keep_default_na=False).drop(columns=["date_basis"], errors="ignore")
man = pd.read_csv(MANUAL, keep_default_na=False)

unknown = set(man.tokenizer_id) - set(reg.tokenizer_id)
if unknown:
    raise SystemExit(f"Unknown tokenizer ids in manual file: {sorted(unknown)}")

man = man.set_index("tokenizer_id")
for col in ["release_date", "source_url"]:
    for tok_id, val in man[col].items():
        if val != "":
            reg.loc[reg.tokenizer_id == tok_id, col] = val
reg["date_basis"] = reg.tokenizer_id.map(man["date_basis"]).fillna("TODO")

reg.to_csv(REG, index=False)
todo = int((reg == "TODO").sum().sum())
print(reg[["tokenizer_id", "release_date", "date_basis"]].to_string(index=False))
print(f"\nRemaining TODO cells: {todo}")