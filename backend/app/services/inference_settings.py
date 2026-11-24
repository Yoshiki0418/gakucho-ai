"""Validated, request-scoped chat settings; importing this module loads no models."""

import os
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_MODEL = "gpt-5.2"
LIMITS = {
    "temperature": {"min": 0, "max": 2},
    "max_tokens": {"min": 16, "max": 4096},
    "rag_top_k": {"min": 1, "max": 20},
    "rag_threshold": {"min": 0, "max": 1},
}


def model_options(kind: str = "llm") -> list[dict]:
    """Deployment-controlled allowlist, independent of a user's query parameters."""
    key = "GAKUCHO_LLM_MODELS" if kind == "llm" else "GAKUCHO_FILLER_MODELS"
    names = os.getenv(key, "gpt-5.2,gpt-4o,gpt-4o-mini").split(",")
    names = list(
        dict.fromkeys([DEFAULT_MODEL] + [n.strip() for n in names if n.strip()])
    )
    return [
        {
            "id": name,
            "label": name,
            # Only expose sampling controls for the known compatible model family.
            "supports_temperature": name.startswith("gpt-4o"),
        }
        for name in names
    ]


class InferenceSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    llm_model: str | None = Field(default=None, max_length=100)
    filler_model: str | None = Field(default=None, max_length=100)
    mode: Literal["general", "ceremony", "assistant", "baseline"] = "general"
    filler_mode: Literal[
        "dynamic", "external", "static", "none", "off", "endogenous"
    ] = "dynamic"
    temperature: float | None = Field(default=None, ge=0, le=2, allow_inf_nan=False)
    max_tokens: int | None = Field(default=None, ge=16, le=4096)
    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_threshold: float = Field(default=0.25, ge=0, le=1, allow_inf_nan=False)
    tts_voice: int = Field(default=0, ge=0, le=65535)


def parse_settings(query: Mapping[str, str]) -> InferenceSettings:
    values = {
        name: query[name] for name in InferenceSettings.model_fields if name in query
    }
    if (
        "filler_mode" not in values
        and query.get("filler_enabled", "true").lower() != "true"
    ):
        values["filler_mode"] = "off"
    settings = InferenceSettings.model_validate(values)
    for key, kind in (("llm_model", "llm"), ("filler_model", "filler")):
        value = getattr(settings, key)
        if value is not None and value not in {m["id"] for m in model_options(kind)}:
            raise ValueError(f"{key}: 利用可能なモデルを選択してください。")
    if settings.temperature is not None:
        selected = settings.llm_model or DEFAULT_MODEL
        compatible = next(
            m["supports_temperature"] for m in model_options() if m["id"] == selected
        )
        if not compatible:
            raise ValueError(
                "temperature: 選択したモデルは温度設定に対応していません。"
            )
    return settings


def settings_catalog(tts_voices: list[dict], stt_models: list[dict]) -> dict:
    return {
        "llm_models": model_options(),
        "filler_models": model_options("filler"),
        "tts_voices": tts_voices,
        "stt_models": stt_models,
        "modes": [
            {
                "id": "general",
                "label": "学長モード",
                "description": "学長として対話し、学内検索・専門エージェントを利用します。",
            },
            {
                "id": "assistant",
                "label": "一般AIモード",
                "description": "学長を名乗らず回答します。学内検索・専門エージェント・外部フィラーは使いません。",
            },
            {
                "id": "ceremony",
                "label": "式典モード",
                "description": "学長として式典向けに簡潔に回答します。",
            },
        ],
        "defaults": {
            "llm_model": DEFAULT_MODEL,
            "filler_model": DEFAULT_MODEL,
            "mode": "general",
            "temperature": None,
            "max_tokens": None,
            "rag_top_k": 5,
            "rag_threshold": 0.25,
            "tts_voice": str(tts_voices[0]["id"]) if tts_voices else "0",
            "stt_model": "browser",
        },
        "limits": LIMITS,
        "scope": {
            "llm_model": "親の会話エージェント。専門エージェント・RAG・意図分類のモデルは変わりません。",
            "temperature": "親の会話エージェントとRAG回答。対応するモデルでのみ指定できます。",
            "max_tokens": "親の会話エージェントとRAG回答。",
            "rag": "会話が学内検索へ振り分けられた場合の検索条件。一般AIモードでは使用しません。",
            "apply": "次の送信から、この会話のリクエストだけに適用します。",
        },
    }
