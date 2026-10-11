"""Single source of truth for the tokenizers used in the project.

Add or change a tokenizer here only; scripts 02, 04, 05 and 06 import this file.
"""
from transformers import AutoTokenizer

# tokenizer_id -> (tiktoken encoding name, organisation, generation_order)
TIKTOKEN = {
    "gpt2": ("gpt2", "OpenAI", 1),
    "cl100k_base": ("cl100k_base", "OpenAI", 2),
    "o200k_base": ("o200k_base", "OpenAI", 3),
}

# tokenizer_id -> (Hugging Face repo id, organisation, generation_order)
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

# Closed models counted with the providers' free token-counting endpoints (script 06).
# tokenizer_id -> (provider, model_api_name, organisation, generation_order)
# generation_order of the two Claude models is an ASSUMPTION (Haiku 4.5 older tokenizer,
# Sonnet 5.5 newer); the counts will show whether it holds.
API = {
    "claude_haiku_4_5": ("anthropic", "claude-haiku-4-5-20251001", "Anthropic", 1),
    "claude_sonnet_5_5": ("anthropic", "claude-sonnet-5-5", "Anthropic", 2),
    "gemini_3_8_flash": ("google", "gemini-3.8-flash", "Google", 1),
}

# generation_order is comparable only inside one family.
FAMILY = {
    "gpt2": "gpt", "cl100k_base": "gpt", "o200k_base": "gpt",
    "qwen2.5": "qwen", "qwen3": "qwen",
    "gemma2": "gemma", "gemma3": "gemma",
    "llama3": "llama",
    "mistral_nemo": "mistral",
    "claude_haiku_4_5": "claude", "claude_sonnet_5_5": "claude",
    "gemini_3_8_flash": "gemini",
}


def load_hf_tokenizer(tok_id):
    repo = HF[tok_id][0]
    return AutoTokenizer.from_pretrained(repo, **HF_KWARGS.get(tok_id, {}))