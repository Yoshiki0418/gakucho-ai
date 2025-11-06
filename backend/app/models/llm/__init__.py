"""
LLM モジュールパッケージ
BaseLLM（抽象基底）と OpenAILLM（実装クラス）を提供。
"""

from .base_llm import BaseLLM
from .openai_llm import OpenAILLM

__all__ = ["BaseLLM", "OpenAILLM"]
