"""Constants shared by the data layer and the views.

Everything here is either a display label or a value that is documented in
data_dictionary.md. Nothing in this file is a data value that the app shows
as a result: results are always computed from the CSV files in data/.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
SOURCE_DIR = ROOT / "data" / "source"
REFERENCE_DIR = ROOT / "data" / "reference"

QUESTION = (
    "Is the extra token cost of non-English languages a fixed property of "
    "their scripts, or a result of tokeniser design choices that is shrinking?"
)
PERSONA = (
    "Pricing and monetisation lead at a global AI service, who sets prices and usage quotas for users in many languages and must decide whether to absorb the extra "
    "token cost, price it into plans and quotas, or invest in a better tokeniser. They need to see where the unfairness is, how large it is in cost terms, "
    "and whether a newer tokeniser would fix it."
)

# Background paragraph shown before the question. Every claim is from one of the four papers listed in BACKGROUND_PAPERS.
CONTEXT = (
    "AI language models bill text in tokens rather than words, and most tokenisers are trained primarily on English. As a result, the same content in languages such as Burmese, "
    "Tamil or Amharic can require several times more tokens, potentially making AI services more expensive for their users. Earlier research found gaps of up to 15× "
    "between equivalent translations on the tokeniser behind ChatGPT and GPT-4 (Petrov et al., 2023). More recent studies suggest that while part of this difference reflects "
    "how languages are written, tokeniser design can substantially reduce the gap without greatly sacrificing efficiency (Arnett et al., 2025; Foroutan et al., 2026).\n\n"
    "This dashboard compares 15 languages across 12 tokenisers to examine how large these differences remain, whether they are shrinking, and what they imply for pricing, "
    "quotas and equitable access to AI systems."
)

# Plain-language definitions shown in the Glossary expander.
GLOSSARY = (
    "- **Token**: the chunk of text a model reads and bills for. It can be a short word, part of a longer word, or a single character.\n"
    "- **Tokeniser**: the tool that cuts text into tokens. Each model family has its own. One built mostly around English cuts other languages into more pieces.\n"
    "- **Premium**: how many times more tokens a language needs than English for the same sentences on the same tokeniser. English is 1.0×; 3.0× means three times the tokens, "
    "so three times the bill when billing is per token.\n"
    "- **Bytes and byte premium**: a byte is a unit of storage size. The byte premium is the same ratio as the premium but counts bytes instead of tokens. "
    "It shows how much of the gap comes from how the language is written, not from the tokeniser.\n"
    "- **Gini coefficient**: a score from 0 to 1 for how unequal the costs are across languages. 0 means every language costs the same; higher means more unequal.\n"
    "- **Buffer**: a language's premium varies from sentence to sentence. The buffer is the extra tokens (as a % above the average premium) "
    "needed so that a chosen share of sentences, such as 95%, fits inside a quota.\n"
    "- **Tier and overcharge**: a tier is a group of languages that pay the same price multiplier, set at the group's costliest language. "
    "Overcharge is how much more a language pays than its real premium (0% means it pays exactly its real cost).\n"
    "- **Quota**: the number of tokens a user may use. An English-equivalent quota is the allowance that the same content would use in English."
)
BACKGROUND_PAPERS = (
    "Petrov, La Malfa, Torr and Bibi (2023). Language Model Tokenizers Introduce Unfairness Between Languages. NeurIPS 2023.",
    "Foroutan, Meister, Paul, Niklaus, Ahmadi, Bosselut and Sennrich (2026). Parity-Aware Byte-Pair Encoding: Improving Cross-lingual Fairness in Tokenization. ACL 2026 (long papers).",
    "Arnett, Chang, Biderman and Bergen (2025). Explaining and Mitigating Crosslingual Tokenizer Inequities. arXiv:2510.21909.",
    "Lundin, Zhang, Karim, Louzan, Wei, Adelani and Carroll (2026). The Token Tax: Systematic Bias in Multilingual Tokenization. AfricaNLP 2026.",
)

# Dates from data_dictionary.md. tests/test_data.py checks the ones that can
# be read from a data file (prices, API counts) against the files themselves.
FLORES_RETRIEVED = "2026-10-07"
TOKEN_COUNTS_RUN = "2026-10-11"
LAST_REFRESH = "2026-10-11"

TOKENIZER_LABELS = {
    "gpt2": "GPT-2",
    "cl100k_base": "cl100k",
    "o200k_base": "o200k",
    "qwen2.5": "Qwen2.5",
    "qwen3": "Qwen3",
    "gemma2": "Gemma 2",
    "gemma3": "Gemma 3",
    "llama3": "Llama 3.2",
    "mistral_nemo": "Mistral Nemo",
    "claude_haiku_4_5": "Claude Haiku 4.5",
    "claude_sonnet_5_5": "Claude Sonnet 5.5",
    "gemini_3_8_flash": "Gemini 3.8 Flash",
}
FAMILY_LABELS = {
    "gpt": "GPT",
    "qwen": "Qwen",
    "gemma": "Gemma",
    "llama": "Llama",
    "mistral": "Mistral",
    "claude": "Claude",
    "gemini": "Gemini",
}
# Fixed order = fixed colour slot. A family keeps its colour whatever is filtered.
FAMILY_ORDER = ["gpt", "qwen", "gemma", "claude", "llama", "mistral", "gemini"]

DEFAULT_TOKENIZER = "o200k_base"
ENGLISH = "eng_Latn"

# ISO 15924 script codes (lang_meta.csv iso_15924) as display names.
SCRIPT_NAMES = {
    "Latn": "Latin",
    "Cyrl": "Cyrillic",
    "Arab": "Arabic",
    "Hans": "Han",
    "Jpan": "Japanese",
    "Hang": "Hangul",
    "Deva": "Devanagari",
    "Taml": "Tamil",
    "Thai": "Thai",
    "Mymr": "Myanmar",
    "Ethi": "Ethiopic",
}

# Validated categorical palette, light mode (dataviz skill, references/palette.md).
# Slots 1-7 pass the adjacent-pair colour-vision check (node validate_palette.js).
SERIES = [
    "#2a78d6",  # 1 blue
    "#eb6834",  # 2 orange
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 yellow
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 green
    "#6250d6",  # 7 violet
    "#e34948",  # 8 red
]
BLUE = SERIES[0]
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"
