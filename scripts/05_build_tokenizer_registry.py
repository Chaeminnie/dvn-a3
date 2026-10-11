"""Step 6: Build the tokenizer registry.

Output: data/source/tokenizers.csv

vocab_size: tiktoken n_vocab, or len(tokenizer) for Hugging Face (includes added/special
tokens). Closed models counted through an API have no inspectable vocabulary ("n/a").
organisation, family and generation_order come from scripts/tokenizer_config.py;
generation_order is comparable only within one family. release_date is filled by hand from
the official source; rows marked TODO must be completed before submission.
Only tokenizers present in token_counts_long.csv are listed.
"""
from pathlib import Path

import pandas as pd
import tiktoken

from tokenizer_config import TIKTOKEN, HF, HF_KWARGS, API, FAMILY, load_hf_tokenizer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "source" / "tokenizers.csv"
COUNTS = ROOT / "data" / "processed" / "token_counts_long.csv"
counted = set(pd.read_csv(COUNTS)["tokenizer_id"]) if COUNTS.exists() else None

API_DOCS = {
    "anthropic": "https://platform.claude.com/docs/en/build-with-claude/token-counting",
    "google": "https://ai.google.dev/gemini-api/docs/tokens",
}


def wanted(tok_id):
    return counted is None or tok_id in counted


rows = []
for tok_id, (enc_name, org, order) in TIKTOKEN.items():
    if not wanted(tok_id):
        continue
    enc = tiktoken.get_encoding(enc_name)
    rows.append({
        "tokenizer_id": tok_id, "library": "tiktoken", "source_name": enc_name,
        "vocab_size": enc.n_vocab, "organisation": org,
        "family": FAMILY.get(tok_id, org), "generation_order": order,
        "load_args": "", "release_date": "TODO", "source_url": "TODO",
    })

for tok_id, (repo, org, order) in HF.items():
    if not wanted(tok_id):
        continue
    tok = load_hf_tokenizer(tok_id)
    rows.append({
        "tokenizer_id": tok_id, "library": "transformers", "source_name": repo,
        "vocab_size": len(tok), "organisation": org,
        "family": FAMILY.get(tok_id, org), "generation_order": order,
        "load_args": str(HF_KWARGS.get(tok_id, "")), "release_date": "TODO",
        "source_url": f"https://huggingface.co/{repo}",
    })

for tok_id, (provider, model, org, order) in API.items():
    if not wanted(tok_id):
        continue
    rows.append({
        "tokenizer_id": tok_id, "library": "api", "source_name": model,
        "vocab_size": "n/a", "organisation": org,
        "family": FAMILY.get(tok_id, org), "generation_order": order,
        "load_args": "free token-counting endpoint; constant message overhead subtracted",
        "release_date": "TODO", "source_url": API_DOCS[provider],
    })

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)
print(df.to_string(index=False))
print(f"\nWrote {OUT}")