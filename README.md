# Do some languages cost more tokens than others?

DVN Assignment 3 — AI & Language Inequality.

## Question

**Is the extra token cost of non-English languages a fixed property of their scripts, or a result of tokenizer design choices that is shrinking?**

AI services charge per token. The same sentence needs a different number of tokens in different languages, so the same message can cost a Burmese or Tamil user several times what it costs an English user. We measure that gap across 12 tokenizers and 15 languages and ask whether it is a fixed property of the scripts or something tokenizer design can change.

## Persona

**Pricing & monetisation lead at a global AI service.** They set prices and usage quotas for users in many languages and must decide whether to:
1. absorb the extra token cost,
2. price it into plans and quotas, or
3. invest in a better tokenizer.

They need to see where the unfairness is, how large it is in money terms, and whether a newer tokenizer would fix it.

## User stories

1. **Cost vs English.** As a pricing lead, I want to see how many more tokens each language needs than English, for each tokenizer, so that I know where per-language cost differences come from.
2. **My language mix.** As a monetisation manager, I want to enter my user language mix and a token quota, so that I can see how many requests and how much cost per user each language gets.
3. **Is it shrinking?** As a budget owner, I want to see how the premium changes across tokenizers and generations (for example Gemma 2 to Gemma 3), so that I can decide whether to invest in a better tokenizer or wait.

## Data (v1)

- 15 languages x 200 FLORES+ devtest sentences (fixed-seed sample; the same sentence in every language).
- 12 tokenizers: 9 run locally (GPT-2, cl100k, o200k, Qwen2.5, Qwen3, Gemma 2, Gemma 3, Llama 3.2, Mistral Nemo) and 3 counted through the providers' free token-counting APIs (Claude Haiku 4.5, Claude Sonnet 5.5, Gemini 3.8 Flash).
- Premium = total tokens for a language divided by total tokens for English, same tokenizer, same sentences (English = 1.0). Also given: UTF-8 byte premium (encoding-only baseline) and a Gini coefficient per tokenizer (0 = every language costs the same).

| File | What it holds |
|---|---|
| `data/processed/token_counts_long.csv` | tokens per sentence, language and tokenizer (36,000 rows) |
| `data/processed/token_premium.csv` | premium vs English, byte premium, mean tokens per sentence (180 rows) |
| `data/processed/tokenizer_gini.csv` | inequality per tokenizer (12 rows) |
| `data/processed/sample_vs_full_check.csv` | sample vs full devtest check, local tokenizers (135 rows) |
| `data/source/` | sentence sample, language and tokenizer tables, prices, language mix, raw API counts |

Everything is documented in [`data_dictionary.md`](data_dictionary.md): sources, licences, columns, keys, transforms and limitations.

## First findings (sample of 200 sentences, about +/-3%)

- The same language costs very different amounts across tokenizers: Burmese is 2.4x English on Gemma 3 / Gemini 3.8 Flash but 17.1x on GPT-2 and 11.8x on Llama 3.2.
- Newer is not automatically fairer: Gemma 2 to Gemma 3 cut the Gini from 0.25 to 0.12 (the lowest of all 12), while Llama 3.2 has the highest Gini (0.43).
- Claude Sonnet 5.5 produces 33-46% more tokens than Haiku 4.5 for Latin-script languages and about the same for the others. Its premiums look lower only because English got more expensive, so charts should show absolute tokens next to ratios.
- Qwen2.5 = Qwen3 and Gemma 3 = Gemini 3.8 Flash give identical counts, so they are not independent data points.

## How to run

Requirements: Python 3.9+. Hugging Face access to FLORES+, Gemma and Llama is needed only for the full rebuild (`--full`).

```bash
git clone https://github.com/Chaeminnie/dvn-a3.git
cd dvn-a3
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

bash run_all.sh                 # core: rebuilds every processed file, no API keys needed
bash run_all.sh --refresh-api   # also re-fetch Claude/Gemini counts (needs a .env file with ANTHROPIC_API_KEY and GEMINI_API_KEY)
bash run_all.sh --full          # also re-download FLORES+ and re-run the sample-vs-full check (needs a Hugging Face login)
```

After `bash run_all.sh`, `git status --short` should show no changes.

Pipeline: `scripts/01_fetch_flores.py` to `02_count_tokens.py` to `03_aggregate.py` to `04_validate_sample.py`, plus `05_build_tokenizer_registry.py`, `05b_apply_manual_fields.py` and `06_fetch_api_counts.py`. Tokenizers are defined once in `scripts/tokenizer_config.py`. Hand-maintained fields (release dates, source URLs) live in `data/source/tokenizers_manual.csv`.

## Known limitations

- 15 languages chosen by the team; the Gini depends on this set.
- 200-sentence sample (max observed sampling error 3.13%); FLORES+ is translated text.
- Token counts only, list prices only, input tokens only in the calculator plan.
- `language_mix.csv` is an equal-weight placeholder, not real usage data.
- Claude Haiku 5.5 is the current Haiku but was not counted.
- 9 of 12 tokenizer release dates are not yet verified (`date_basis` column).

## Licences and attribution

- Sentences: FLORES+ (CC BY-SA 4.0), Open Language Data Initiative, based on FLORES-200 (NLLB Team et al., 2022). The share-alike term applies to the sample file.
- Tokenizers: see `data_dictionary.md` (a few licences are still marked TODO).

## Team

[TODO: names and roles]

## Status

Data v1 is complete. Next: charts, the interactive cost calculator, and the AI provenance matrix.
