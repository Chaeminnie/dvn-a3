from datasets import load_dataset, get_dataset_config_names
import tiktoken

DS = "openlanguagedata/flores_plus"

configs = get_dataset_config_names(DS)
print("number of configs:", len(configs))
print("first 10:", configs[:10])
print("eng-like:", [c for c in configs if c.startswith("eng")])
print("kor-like:", [c for c in configs if c.startswith("kor")])

cfg = "eng_Latn" if "eng_Latn" in configs else configs[0]
ds = load_dataset(DS, cfg, split="devtest")
print("config used:", cfg)
print("rows:", len(ds))
print("columns:", ds.column_names)
text = ds[0]["text"]
print(text)

for name in ["cl100k_base", "o200k_base"]:
    enc = tiktoken.get_encoding(name)
    print(name, len(enc.encode_ordinary(text)))
