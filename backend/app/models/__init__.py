"""
モデルの共通インスタンスを初期化するモジュール。

・環境変数 (.env) に基づいて LLM / TTS を生成
・アプリ内からは常に `from app.models import llm, tts` でアクセス可能
"""

from .model_registry import load_models_from_env

# モデルの共通インスタンスをロード
llm, tts = load_models_from_env()

__all__ = ["llm", "tts"]
