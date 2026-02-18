# app/models/local_llm.py など

from typing import AsyncIterator, List, Optional

from app.models.llm import BaseLLM


class LocalLLM(BaseLLM):
    """ローカルLLM（仮実装）。BaseLLMの抽象メソッドを最低限埋める。"""

    def __init__(self, model_name: str, system_prompt: str):
        super().__init__(model_name, system_prompt)

    # ───────────────────────────────
    # コンテキスト構築（仮）
    # ───────────────────────────────
    def build_context(
        self,
        message: str,
        system_prompt: str,
        history: Optional[List[dict[str, str]]] = None,
        tool_calls: Optional[List[dict[str, str]]] = None,
    ) -> list[dict[str, str]]:
        """とりあえずユーザー発話だけを返す仮実装"""
        return [{"role": "user", "content": message}]

    # ───────────────────────────────
    # 非ストリーミング生成（仮）
    # ───────────────────────────────
    async def _generate_impl(
        self,
        message: str,
        history: Optional[List[dict[str, str]]] = None,
        tool_calls: Optional[List[dict[str, str]]] = None,
        max_tokens: int = 150,
        temperature: float = 0.8,
    ) -> str:
        """仮の応答を返すだけ"""
        return f"(ローカルLLMの仮応答) あなたの発話: {message}"

    # ───────────────────────────────
    # ストリーミング生成（仮）
    # ───────────────────────────────
    async def stream_generate(
        self,
        message: str,
        history: Optional[List[dict[str, str]]] = None,
        tool_calls: Optional[List[dict[str, str]]] = None,
    ) -> AsyncIterator[str]:
        """ストリーミング用のダミー出力"""
        yield f"(streaming) {message}"
