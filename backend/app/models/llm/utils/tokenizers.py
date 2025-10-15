import tiktoken
from transformers import AutoTokenizer

_cached = {}


def get_tokenizer(model_name: str):
    """モデル名に応じてトークナイザーを自動選択"""
    if model_name in _cached:
        return _cached[model_name]

    # --- OpenAI系列 ---
    try:
        enc = tiktoken.encoding_for_model(model_name)
        _cached[model_name] = enc.encode
        return enc.encode
    except KeyError:
        pass

    # --- HuggingFace系列 ---
    try:
        tok = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        _cached[model_name] = tok.encode
        return tok.encode
    except Exception:
        pass

    # --- fallback ---
    def naive_tokenizer(text: str):
        return text.split()

    _cached[model_name] = naive_tokenizer
    return naive_tokenizer
