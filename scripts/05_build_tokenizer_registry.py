"""Step 6: Build the tokenizer registry.

Output: data/source/tokenizers.csv

Columns read from the libraries (auto): vocab_size
Columns filled by hand (manual): organisation, generation_order, source_url, release_date
  - generation_order is only meaningful within one organisation (1 = oldest).
  - Fill release_date and source_url from the official page, and keep the URL.
    Rows marked TODO must be completed before submission (data dictionary check).
"""
from pathlib import Path

import pandas as pd
import tiktoken
from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "source" / "tokenizers.csv"

TIKTOKEN_IDS = {
    "gpt2": ("OpenAI", 1),
    "cl100k_base": ("OpenAI", 2),
    "o200k_base": ("OpenAI", 3),
}
HF_IDS = {
    "qwen2.5": ("Qwen/Qwen2.5-0.5B", "Alibaba (Qwen)", 1),
    "gemma2": ("google/gemma-2-2b", "Google", 1),
    "llama3": ("meta-llama/Llama-3.2-1B", "Meta", 1),
}

rows = []
for tok_id, (org, order) in TIKTOKEN_IDS.items():
    enc = tiktoken.get_encoding(tok_id)
    rows.append({
        "tokenizer_id": tok_id,
        "library": "tiktoken",
        "source_name": tok_id,
        "vocab_size": enc.n_vocab,
        "organisation": org,
        "generation_order": order,
        "release_date": "TODO",
        "source_url": "TODO",
    })

for tok_id, (repo, org, order) in HF_IDS.items():
    tok = AutoTokenizer.from_pretrained(repo)
    rows.append({
        "tokenizer_id": tok_id,
        "library": "transformers",
        "source_name": repo,
        "vocab_size": len(tok),  # includes added/special tokens; document this
        "organisation": org,
        "generation_order": order,
        "release_date": "TODO",
        "source_url": f"https://huggingface.co/{repo}",
    })

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)
print(df.to_string(index=False))
print(f"\nWrote {OUT}")
