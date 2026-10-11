"""Step 6: Build the tokenizer registry.

Output: data/source/tokenizers.csv

vocab_size is read from the libraries (tiktoken n_vocab, or len(tokenizer) which
includes added/special tokens; document this). organisation and generation_order
come from scripts/tokenizer_config.py. release_date is filled by hand from the
official source; rows marked TODO must be completed before submission.
"""
from pathlib import Path

import pandas as pd
import tiktoken

from tokenizer_config import TIKTOKEN, HF, HF_KWARGS, load_hf_tokenizer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "source" / "tokenizers.csv"

rows = []
for tok_id, (enc_name, org, order) in TIKTOKEN.items():
    enc = tiktoken.get_encoding(enc_name)
    rows.append({
        "tokenizer_id": tok_id,
        "library": "tiktoken",
        "source_name": enc_name,
        "vocab_size": enc.n_vocab,
        "organisation": org,
        "generation_order": order,
        "load_args": "",
        "release_date": "TODO",
        "source_url": "TODO",
    })

for tok_id, (repo, org, order) in HF.items():
    tok = load_hf_tokenizer(tok_id)
    rows.append({
        "tokenizer_id": tok_id,
        "library": "transformers",
        "source_name": repo,
        "vocab_size": len(tok),
        "organisation": org,
        "generation_order": order,
        "load_args": str(HF_KWARGS.get(tok_id, "")),
        "release_date": "TODO",
        "source_url": f"https://huggingface.co/{repo}",
    })

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)
print(df.to_string(index=False))
print(f"\nWrote {OUT}")