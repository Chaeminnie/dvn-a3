# Data dictionary

Project: DVN Assignment 3 — do some languages cost more tokens than others?
Last updated: 2026-10-11. Data pipeline: Chaemin Jin.

Conventions
- PK = primary key. "Premium" = total tokens for a language divided by total tokens for English, same tokenizer, same FLORES+ sentences (English = 1.0).
- Token counts exclude special tokens (BOS/EOS) and use Unicode NFC-normalised text.
- Regenerate all processed files with `bash run_all.sh` (see run_all.sh for options).
- Tokenizers are defined once in `scripts/tokenizer_config.py`.

## Source files (data/source/)

### flores_sample.csv
- Source: FLORES+ devtest, https://huggingface.co/datasets/openlanguagedata/flores_plus (Hugging Face, gated; terms accepted).
- Licence: CC BY-SA 4.0. This file redistributes a subset of sentences. Attribution: Open Language Data Initiative (OLDI), based on FLORES-200 (NLLB Team et al., 2022, arXiv:2207.04672). Share-alike applies.
- Columns: `lang_code` (text; FLORES+ config name `language_script`, e.g. `kor_Hang`), `sent_id` (integer; FLORES+ `id`; the same id is the same sentence translated into every language), `text` (text; sentence as released).
- PK: (`lang_code`, `sent_id`). Rows: 3,000 (15 languages x 200 sentences).
- Time coverage: not a time series. Retrieved 2026-10-07. Hugging Face dataset revision hash: TODO (not recorded).
- Transform: `scripts/01_fetch_flores.py` downloads the 1,012-sentence devtest per language, validates it (1,012 rows, unique ids, no empty text, same id set as English) and keeps a sample of 200 ids drawn with fixed seed 42 (same ids for all languages). The full devtest stays local (git-ignored).

### lang_meta.csv
- Source: written by the project team; codes follow FLORES+ config names.
- Licence: project-authored; same as the repository.
- Columns: `lang_code` (text), `iso_639_3` (text), `iso_15924` (text, script), `language` (text, display name), `uses_spaces` (text: yes / partial / no).
- PK: `lang_code`. Rows: 15.
- Note: `uses_spaces` is a manual classification by the team, not taken from an external source.
- Transform: `scripts/01_fetch_flores.py` (the LANGS list).

### tokenizers.csv
- Source: libraries, Hugging Face tokenizer repositories (only tokenizer files, not model weights) and the providers' token-counting endpoints.
- Columns: `tokenizer_id` (text), `library` (tiktoken / transformers / api), `source_name` (text; tiktoken encoding, Hugging Face repo id or API model name), `vocab_size` (integer; `n_vocab` for tiktoken, `len(tokenizer)` for Hugging Face, which includes added/special tokens; "n/a" for API models), `organisation` (text), `family` (text), `generation_order` (integer; 1 = oldest; comparable only within one family), `load_args` (text; extra arguments used when loading), `release_date` (TODO), `source_url` (TODO for tiktoken).
- PK: `tokenizer_id`. Rows: 12. Retrieved: 2026-10-11.
- Licences: Qwen3-0.6B Apache-2.0 and Mistral-Nemo-Instruct-2407 Apache-2.0 (checked on the model pages 2026-10-07); gemma-3-1b-it Gemma Terms of Use (gated, terms accepted). TODO to verify: Qwen2.5-0.5B, gemma-2-2b, Llama-3.2-1B (Llama 3.2 Community Licence, gated, terms accepted), tiktoken encodings.
- Notes: `mistral_nemo` is loaded with `fix_mistral_regex=True` because the library warns that the default regex tokenises incorrectly; it was not cross-checked against an independent implementation. Mistral Nemo dates from 2024, so it is a 2024 Tekken baseline. Qwen2.5 and Qwen3 produced identical counts in every cell; whether they share the vocabulary is TODO. The generation_order of the two Claude models is an assumption based on the provider's pricing page (Claude 4.7 and later use a newer tokenizer).
- Transform: `scripts/tokenizer_config.py` (definitions) and `scripts/05_build_tokenizer_registry.py`.
- Qwen2.5 and Qwen3 gave identical token counts for all 3,000 sample sentences, and Gemma 3 and Gemini 3.8 Flash did too (checked 2026-10-11). Treat each pair as one tokenizer in comparisons. The Gemma 3 / Gemini match also supports the Gemini overhead calibration (1 token); it was not verified against an official statement.

### prices.csv
- Source: official provider pricing pages (Anthropic https://platform.claude.com/docs/en/about-claude/pricing; Google https://ai.google.dev/gemini-api/docs/pricing), plus one illustrative row.
- Columns: `price_id`, `provider`, `model_api_name`, `tokenizer_id`, `input_usd_per_1m` and `output_usd_per_1m` (USD per 1M tokens), `price_note`, `valid_from` and `valid_until` (dates), `source_tier` (official / assumption), `source_url`, `collected_on` (date).
- PK: `price_id`. Rows: 5. Collected 2026-10-11 (prices unchanged since 2026-10-07); re-check before submission. The Gemini 3.8 Flash price changes on 2027-01-01 and has one row per period.
- Scope: list prices for input and output tokens. Cached, batch, priority and regional prices are not modelled. The `illustrative` row is an assumption, not a quote. Claude Haiku 4.5 is no longer the current Haiku (Haiku 5.5 is listed first on the pricing page) and Haiku 5.5 was not counted.

### language_mix.csv
- Source: none. Placeholder with equal weights (1/15 per language).
- Columns: `lang_code` (text), `user_share` (decimal, share of users; sums to about 1), `source_tier` (assumption), `note` (text).
- PK: `lang_code`. Rows: 15.
- Note: this is NOT real usage data. It will be replaced by a sourced dataset or user input in the app.
- Transform: generated from `lang_meta.csv` (one-line script).

### api_token_counts_raw.csv
- Source: free token-counting endpoints of Anthropic (https://platform.claude.com/docs/en/build-with-claude/token-counting) and Google Gemini (https://ai.google.dev/gemini-api/docs/tokens), called on the committed sample sentences. The sentences are FLORES+ (CC BY-SA 4.0) and were sent to the providers' counting endpoints; whether Gemini's free tier uses counting inputs to improve products was not verified.
- Columns: `tokenizer_id`, `lang_code`, `sent_id`, `provider`, `model_api_name`, `raw_count` (tokens as returned, includes a constant message overhead), `overhead_tokens` (calibrated overhead for that run), `collected_at` (UTC timestamp).
- PK: (`tokenizer_id`, `lang_code`, `sent_id`). Rows: 9,000 (3 models x 3,000 sentences). Collected 2026-10-11.
- Counts only: no token boundaries and no round-trip check.
- Transform: `scripts/06_fetch_api_counts.py` (needs API keys; run only with `bash run_all.sh --refresh-api`). `scripts/02_count_tokens.py` uses n_tokens = raw_count - overhead_tokens.

### api_overhead.csv
- Calibration log: per model, overhead = count of probe words ("a", "the", "and") minus 1. All probes must agree, otherwise the model is skipped. Assumption: each probe is a single token. Overhead used: Haiku 4.5 = 7, Sonnet 5.5 = 8, Gemini 3.8 Flash = 1.
- Columns: `tokenizer_id`, `provider`, `model_api_name`, `overhead_tokens`, `probes`, `calibrated_at`. PK: `tokenizer_id`. Rows: 3.
- Validation (2026-10-11, `scripts/check_api_overhead.py`, not part of the pipeline): for four probe scripts (English, French, Korean, Tamil), the fitted intercept of tokens vs number of repeated words was 7.0 for Haiku 4.5, 8.0 for Sonnet 5.5 (7.0 for Korean) and 1.0 for Gemini 3.8 Flash. The constant-overhead assumption therefore holds within +/-1 token (about 1.5% of a 68-token sentence).

## Processed files (data/processed/)

### token_counts_long.csv
- Columns: `lang_code`, `sent_id`, `tokenizer_id`, `n_tokens` (integer, tokens in the sentence), `n_chars` (integer, characters after NFC), `n_bytes` (integer, UTF-8 bytes).
- PK: (`lang_code`, `sent_id`, `tokenizer_id`). Rows: 36,000 (15 x 200 x 12). Run date: 2026-10-11.
- Transform: `scripts/02_count_tokens.py`. Check: round-trip decode(encode(text)) == text for every sentence of the nine local tokenizers (0 failures). API models have no round-trip check.

### token_premium.csv
- Columns: `lang_code`, `tokenizer_id`, `n_sentences`, `total_tokens`, `total_chars`, `total_bytes`, `mean_tokens_per_sentence`, `premium_vs_en` (ratio to English, same tokenizer), `byte_premium_vs_en` (UTF-8 bytes ratio to English, independent of the tokenizer), `premium_over_byte` (`premium_vs_en` / `byte_premium_vs_en`).
- PK: (`lang_code`, `tokenizer_id`). Rows: 180. Values rounded to 4 decimals.
- Transform: `scripts/03_aggregate.py`. Checks: equal sentence counts per pair; English premium = 1.0.

### tokenizer_gini.csv
- Columns: `tokenizer_id`, `n_languages` (integer), `gini` (0 = all languages cost the same, 1 = extreme inequality, computed over `premium_vs_en`), `gini_byte_baseline` (Gini of the byte premium, the encoding-only reference), `max_premium`, `max_premium_lang`, `median_premium`.
- PK: `tokenizer_id`. Rows: 12. Valid only for the 15 languages in the file; not comparable with Gini values from other studies.
- Transform: `scripts/03_aggregate.py`.

### sample_vs_full_check.csv
- Columns: `lang_code`, `tokenizer_id`, `premium_sample`, `premium_full` (same premium on all 1,012 sentences), `rel_diff` (|sample - full| / full).
- PK: (`lang_code`, `tokenizer_id`). Rows: 135 (the nine local tokenizers only; API models were not checked on the full set).
- Pass rule fixed before running: max relative difference <= 5%. Result: 3.13%, PASS.
- Transform: `scripts/04_validate_sample.py` (needs the local full FLORES+ files; `bash run_all.sh --full`).

## Known limitations
- 15 languages chosen by the team (many non-Latin scripts); the Gini depends on this set.
- 200-sentence sample: premiums carry about +/-3% sampling error (max observed 3.13%, Arabic). The sample was validated on the nine local tokenizers only.
- FLORES+ is translated text, not natural usage.
- Token counts only; no model quality, output tokens or price negotiation.
- API models (Claude, Gemini) are black boxes: counts depend on the provider's current tokenizer and may change.
- On the sample, Claude Sonnet 5.5 produced 33-46% more tokens than Haiku 4.5 for Latin-script languages and about the same for the others. The mechanism is unknown. Because English becomes more expensive, the premium vs English looks lower for non-Latin languages even though their absolute token counts did not change. Show absolute tokens per sentence next to premiums.
- Qwen2.5 and Qwen3 gave identical counts; do not present them as two independent generations until the vocabulary comparison is done.