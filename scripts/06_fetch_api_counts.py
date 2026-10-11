"""Step 7: Count tokens with the free token-counting endpoints of Claude and Gemini.

Closed models do not publish their tokenizers. The counting endpoints return only a
number (no token boundaries), so these models enter the premium and cost analysis but
not the token-boundary visual.

Input:  data/source/flores_sample.csv   (the committed 3,000 sample sentences)
Output: data/source/api_token_counts_raw.csv   raw counts as returned (resumable cache)
        data/source/api_overhead.csv           per-model message overhead (calibration log)

Overhead: Claude wraps the text in a message, so the raw count contains a constant number
of extra tokens. It is measured with probe words that are one token in any modern
vocabulary ("a", "the", "and"): overhead = raw count - 1. All probes must agree, otherwise
that model is skipped. The overhead used is stored in every raw row.

Keys are read from .env (ANTHROPIC_API_KEY, GEMINI_API_KEY). Never print or commit them.
Counting is free but rate-limited; calls are retried with backoff and the script can be
re-run to resume.

Usage:
  python scripts/06_fetch_api_counts.py --per-lang 5   # smoke test
  python scripts/06_fetch_api_counts.py                # full sample
"""
import argparse
import os
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from tokenizer_config import API

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SRC = ROOT / "data" / "source" / "flores_sample.csv"
RAW = ROOT / "data" / "source" / "api_token_counts_raw.csv"
OVERHEAD = ROOT / "data" / "source" / "api_overhead.csv"
PROBES = ["a", "the", "and"]  # one token in any modern vocabulary
FLUSH_EVERY = 100

parser = argparse.ArgumentParser()
parser.add_argument("--per-lang", type=int, default=None,
                    help="only the first N sentences per language (smoke test)")
parser.add_argument("--workers", type=int, default=4)
args = parser.parse_args()


def make_counters():
    counters = {}
    providers = {v[0] for v in API.values()}
    if "anthropic" in providers:
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            print("[skipped] Claude models: ANTHROPIC_API_KEY is missing in .env")
        else:
            import anthropic
            client = anthropic.Anthropic(api_key=key)
            counters["anthropic"] = lambda model, text: client.messages.count_tokens(
                model=model, messages=[{"role": "user", "content": text}]
            ).input_tokens
    if "google" in providers:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            print("[skipped] Gemini models: GEMINI_API_KEY is missing in .env")
        else:
            from google import genai
            gclient = genai.Client(api_key=key)
            counters["google"] = lambda model, text: gclient.models.count_tokens(
                model=model, contents=text
            ).total_tokens
    return counters


def with_retry(fn, *a, tries=6):
    for attempt in range(tries):
        try:
            return fn(*a)
        except Exception as e:
            if attempt == tries - 1:
                raise
            wait = min(60, 2 ** attempt)
            print(f"  retry in {wait}s after {type(e).__name__}", flush=True)
            time.sleep(wait)


def calibrate(counters):
    ok = {}
    for tok_id, (provider, model, _, _) in API.items():
        if provider not in counters:
            continue
        try:
            counts = [with_retry(counters[provider], model, p) for p in PROBES]
        except Exception as e:
            print(f"[skipped] {tok_id} ({model}): {type(e).__name__}: {str(e)[:200]}")
            continue
        overheads = {c - 1 for c in counts}
        print(f"[calibration] {tok_id}: probe counts {dict(zip(PROBES, counts))}")
        if len(overheads) != 1:
            print(f"[skipped] {tok_id}: probes disagree (overheads {sorted(overheads)}). Check by hand.")
            continue
        ok[tok_id] = overheads.pop()
    return ok


counters = make_counters()
overheads = calibrate(counters)
if not overheads:
    sys.exit("No API model could be calibrated. Check the keys and model names above.")
print("Overhead tokens per model:", overheads)

now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
ov_rows = [{"tokenizer_id": t, "provider": API[t][0], "model_api_name": API[t][1],
            "overhead_tokens": o, "probes": "|".join(PROBES), "calibrated_at": now}
           for t, o in overheads.items()]
old_ov = pd.read_csv(OVERHEAD) if OVERHEAD.exists() else pd.DataFrame()
if len(old_ov):
    old_ov = old_ov[~old_ov["tokenizer_id"].isin(list(overheads))]
pd.concat([old_ov, pd.DataFrame(ov_rows)], ignore_index=True).to_csv(OVERHEAD, index=False)

df = pd.read_csv(SRC)
df["text"] = df["text"].map(lambda s: unicodedata.normalize("NFC", s))
if args.per_lang:
    df = df.sort_values(["lang_code", "sent_id"]).groupby("lang_code").head(args.per_lang)

done = set()
if RAW.exists():
    old = pd.read_csv(RAW)
    done = set(zip(old["tokenizer_id"], old["lang_code"], old["sent_id"]))

tasks = [(t, r.lang_code, int(r.sent_id), r.text)
         for t in overheads for r in df.itertuples(index=False)
         if (t, r.lang_code, int(r.sent_id)) not in done]
print(f"{len(tasks)} calls to make ({len(done)} already cached)")


def work(task):
    tok_id, lang, sent_id, text = task
    provider, model = API[tok_id][0], API[tok_id][1]
    raw = with_retry(counters[provider], model, text)
    return {"tokenizer_id": tok_id, "lang_code": lang, "sent_id": sent_id,
            "provider": provider, "model_api_name": model, "raw_count": raw,
            "overhead_tokens": overheads[tok_id], "collected_at": now}


buf, failures, finished = [], 0, 0
start = time.time()


def flush():
    if buf:
        pd.DataFrame(buf).to_csv(RAW, mode="a", header=not RAW.exists(), index=False)
        buf.clear()


with ThreadPoolExecutor(max_workers=args.workers) as pool:
    futures = [pool.submit(work, t) for t in tasks]
    for fut in as_completed(futures):
        try:
            buf.append(fut.result())
        except Exception as e:
            failures += 1
            print(f"  failed: {type(e).__name__}: {str(e)[:120]}", flush=True)
        finished += 1
        if len(buf) >= FLUSH_EVERY:
            flush()
        if finished % 500 == 0:
            print(f"  {finished}/{len(tasks)} done, {finished / (time.time() - start):.1f} calls/s", flush=True)
flush()

elapsed = time.time() - start
print(f"Done: {finished - failures} ok, {failures} failed, {elapsed:.0f}s")
if failures:
    print("Some calls failed. Run the script again to resume; cached results are kept.")

raw = pd.read_csv(RAW)
raw["n_tokens_est"] = raw["raw_count"] - raw["overhead_tokens"]
print("\nMean tokens per sentence (overhead subtracted):")
print(raw.pivot_table(index="lang_code", columns="tokenizer_id",
                      values="n_tokens_est", aggfunc="mean").round(1).to_string())