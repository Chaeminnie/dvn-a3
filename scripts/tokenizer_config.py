"""Single source of truth for the tokenizers used in the project.

Add or change a tokenizer here only; scripts 02, 04 and 05 import this file.
"""
from transformers import AutoTokenizer

# tokenizer_id -> (tiktoken encoding name, organisation, generation_order)
TIKTOKEN = {
    "gpt2": ("gpt2", "OpenAI", 1),
    "cl100k_base": ("cl100k_base", "OpenAI", 2),
    "o200k_base": ("o200k_base", "OpenAI", 3),
}

# tokenizer_id -> (Hugging Face repo id, organisation, generation_order)
# generation_order is only meaningful within one organisation (1 = oldest).
HF = {
    "qwen2.5": ("Qwen/Qwen2.5-0.5B", "Alibaba (Qwen)", 1),
    "qwen3": ("Qwen/Qwen3-0.6B", "Alibaba (Qwen)", 2),
    "gemma2": ("google/gemma-2-2b", "Google", 1),
    "gemma3": ("google/gemma-3-1b-it", "Google", 2),
    "llama3": ("meta-llama/Llama-3.2-1B", "Meta", 1),
    "mistral_nemo": ("mistralai/Mistral-Nemo-Instruct-2407", "Mistral AI", 1),
}

# Extra keyword arguments for specific tokenizers.
# Mistral Nemo: transformers warns that the tokenizer loads with an incorrect regex
# unless fix_mistral_regex=True is set. Document this in the data dictionary.
HF_KWARGS = {
    "mistral_nemo": {"fix_mistral_regex": True},
}


def load_hf_tokenizer(tok_id):
    repo = HF[tok_id][0]
    return AutoTokenizer.from_pretrained(repo, **HF_KWARGS.get(tok_id, {}))