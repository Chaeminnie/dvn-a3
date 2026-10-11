"""Diagnostic: is the message overhead of the counting endpoints really constant?

For each model and each probe word, count 1, 20 and 80 copies of the word separated by
spaces, then fit tokens = intercept + slope * n.
  slope     = tokens per word for that script
  intercept = per-message overhead (should equal the calibrated overhead for every word)
If the intercept differs by script, the constant-overhead assumption in script 06 is wrong.
Free to run (about 36 calls). Not part of the pipeline.
"""
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from tokenizer_config import API

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

WORDS = {"english": "the", "french": "le", "korean": "한국어", "tamil": "தமிழ்"}
NS = [1, 20, 80]


def retry(fn, *a, tries=5):
    for i in range(tries):
        try:
            return fn(*a)
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


counters = {}
if os.getenv("ANTHROPIC_API_KEY"):
    import anthropic
    ac = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    counters["anthropic"] = lambda m, t: ac.messages.count_tokens(
        model=m, messages=[{"role": "user", "content": t}]).input_tokens
if os.getenv("GEMINI_API_KEY"):
    from google import genai
    gc = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    counters["google"] = lambda m, t: gc.models.count_tokens(model=m, contents=t).total_tokens

print(f"{'model':<20}{'word':<9}{'n=1':>6}{'n=20':>7}{'n=80':>7}{'slope':>8}{'intercept':>11}  linear")
for tok_id, (provider, model, _, _) in API.items():
    if provider not in counters:
        continue
    for lang, word in WORDS.items():
        c = [retry(counters[provider], model, " ".join([word] * n)) for n in NS]
        slope = (c[2] - c[0]) / (NS[2] - NS[0])
        intercept = c[0] - slope
        linear = abs((c[0] + slope * (NS[1] - 1)) - c[1]) < 1.01
        print(f"{tok_id:<20}{lang:<9}{c[0]:>6}{c[1]:>7}{c[2]:>7}{slope:>8.2f}{intercept:>11.1f}  {linear}")