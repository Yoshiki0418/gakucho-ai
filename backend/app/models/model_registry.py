import os
from typing import Tuple

from app.models.llm import OpenAILLM
from app.models.tts import StyleBertVITS2_TTS


def create_llm(provider: str, model_name: str = None):
    if provider == "openai":
        return OpenAILLM(model_name=model_name or "gpt-4o-mini")
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def create_tts(provider: str):
    if provider == "style-bert-vits2":
        return StyleBertVITS2_TTS(model_dir="/workspace/backend/app/weights/tts/gakucho_ai")
    else:
        raise ValueError(f"Unknown TTS provider: {provider}")


def load_models_from_env() -> Tuple[object, object]:
    llm_provider = os.getenv("LLM_PROVIDER", "openai")
    llm_model_name = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")
    tts_provider = os.getenv("TTS_PROVIDER", "style-bert-vits2")

    llm = create_llm(llm_provider, llm_model_name)
    tts = create_tts(tts_provider)
    return llm, tts
