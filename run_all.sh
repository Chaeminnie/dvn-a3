#!/usr/bin/env bash
# Regenerate all processed files from the committed source files.
#   bash run_all.sh                 core, no keys needed (uses the committed API counts)
#   bash run_all.sh --refresh-api   also re-fetch Claude/Gemini counts (needs .env keys)
#   bash run_all.sh --full          also re-download FLORES+ and re-run the sample-vs-full check
set -euo pipefail
cd "$(dirname "$0")"

FULL=0
API=0
for arg in "$@"; do
  case "$arg" in
    --full) FULL=1 ;;
    --refresh-api) API=1 ;;
  esac
done

if [[ "$FULL" == "1" ]]; then python scripts/01_fetch_flores.py; fi
if [[ "$API" == "1" ]]; then python scripts/06_fetch_api_counts.py; fi
python scripts/02_count_tokens.py
python scripts/03_aggregate.py
if [[ "$FULL" == "1" ]]; then python scripts/04_validate_sample.py; fi
python scripts/05_build_tokenizer_registry.py