import os
from typing import Tuple

from app.models.llm import OpenAILLM
from app.models.llm.base_llm import BaseLLM
from app.models.tts import StyleBertVITS2_TTS


def read_prompt_from_file(path: str) -> str:
    """システムプロンプトを外部ファイルから読み込む"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"System prompt file not found: {path}")


def create_llm(provider: str, system_prompt: str, model_name: str = None) -> BaseLLM:
    if provider == "openai":
        return OpenAILLM(
            system_prompt=system_prompt, model_name=model_name or "gpt-4o-mini"
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def create_tts(provider: str):
    if provider == "style-bert-vits2":
        return StyleBertVITS2_TTS(
            model_dir="/workspace/backend/app/weights/tts/gakucho_ai_v2"
        )
    else:
        raise ValueError(f"Unknown TTS provider: {provider}")


def load_models_from_env() -> Tuple[object, object]:
    llm_provider = os.getenv("LLM_PROVIDER", "openai")
    llm_model_name = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")
    tts_provider = os.getenv("TTS_PROVIDER", "style-bert-vits2")

    prompt_path = os.getenv(
        "LLM_SYSTEM_PROMPT_PATH", "/workspace/backend/app/prompts/system_prompt.txt"
    )
    system_prompt = read_prompt_from_file(prompt_path)

    llm = create_llm(llm_provider, system_prompt, llm_model_name)
    tts = create_tts(tts_provider)
    return llm, tts
