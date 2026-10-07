"""Step 1: Fetch FLORES+ devtest, validate it, and build the repo-safe sample.

Outputs:
  data/source/flores_full/<lang_code>.csv   full devtest, local only (git-ignored)
  data/source/flores_sample.csv             fixed-seed sample committed to the repo
  data/source/lang_meta.csv                 language metadata (uses_spaces is manual)

Source: openlanguagedata/flores_plus on Hugging Face (CC BY-SA 4.0, gated).
"""
from pathlib import Path
import random

import pandas as pd
from datasets import load_dataset, get_dataset_config_names

DS = "openlanguagedata/flores_plus"
SPLIT = "devtest"
EXPECTED_ROWS = 1012
N_SAMPLE = 200
SEED = 42

# (config name, display name, uses_spaces: yes / partial / no)
# NOTE: uses_spaces is a manual classification. Document it in the data dictionary.
LANGS = [
    ("eng_Latn", "English", "yes"),
    ("fra_Latn", "French", "yes"),
    ("deu_Latn", "German", "yes"),
    ("spa_Latn", "Spanish", "yes"),
    ("rus_Cyrl", "Russian", "yes"),
    ("arb_Arab", "Arabic (Modern Standard)", "yes"),
    ("hin_Deva", "Hindi", "yes"),
    ("tam_Taml", "Tamil", "yes"),
    ("swh_Latn", "Swahili", "yes"),
    ("kor_Hang", "Korean", "yes"),
    ("cmn_Hans", "Chinese (Simplified)", "no"),
    ("jpn_Jpan", "Japanese", "no"),
    ("tha_Thai", "Thai", "no"),
    ("mya_Mymr", "Burmese", "partial"),
    ("amh_Ethi", "Amharic", "yes"),
]

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "data" / "source"
FULL_DIR = SRC_DIR / "flores_full"
FULL_DIR.mkdir(parents=True, exist_ok=True)

# 1) Check that every requested config actually exists on the Hub.
configs = set(get_dataset_config_names(DS))
missing = [code for code, _, _ in LANGS if code not in configs]
if missing:
    for code in missing:
        candidates = sorted(c for c in configs if c.startswith(code[:3]))
        print(f"[MISSING] {code} -> configs for the same language code: {candidates}")
    raise SystemExit("Fix the config names in LANGS above, then run this script again.")

# 2) Download, sort by id, and validate each language.
frames = {}
for code, name, _ in LANGS:
    df = load_dataset(DS, code, split=SPLIT).to_pandas().sort_values("id")
    assert df["id"].is_unique, f"{code}: duplicate ids"
    assert len(df) == EXPECTED_ROWS, f"{code}: expected {EXPECTED_ROWS} rows, got {len(df)}"
    assert df["text"].str.strip().str.len().min() > 0, f"{code}: empty sentence found"
    print(f"{code}: OK, variant values = {df['variant'].unique().tolist()}")
    frames[code] = df
    df[["id", "text"]].to_csv(FULL_DIR / f"{code}.csv", index=False)

# 3) Check that all languages share the same id set as English.
#    The same id means the same sentence translated, so we can compare across languages.
base_ids = set(frames["eng_Latn"]["id"])
for code, df in frames.items():
    assert set(df["id"]) == base_ids, f"{code}: id set differs from English"

# 4) Draw a fixed-seed sample of ids (the same ids for every language).
sample_ids = sorted(random.Random(SEED).sample(sorted(base_ids), N_SAMPLE))
rows = []
for code, df in frames.items():
    subset = df[df["id"].isin(sample_ids)]
    for _, r in subset.iterrows():
        rows.append({"lang_code": code, "sent_id": int(r["id"]), "text": r["text"]})
sample_df = pd.DataFrame(rows)
sample_df.to_csv(SRC_DIR / "flores_sample.csv", index=False)

# 5) Write the language metadata draft.
meta = [
    {
        "lang_code": code,
        "iso_639_3": code.split("_")[0],
        "iso_15924": code.split("_")[1],
        "language": name,
        "uses_spaces": spaces,
    }
    for code, name, spaces in LANGS
]
pd.DataFrame(meta).to_csv(SRC_DIR / "lang_meta.csv", index=False)

print(f"Done: {len(LANGS)} languages, {N_SAMPLE} sampled sentences each, {len(sample_df)} rows in the sample file.")