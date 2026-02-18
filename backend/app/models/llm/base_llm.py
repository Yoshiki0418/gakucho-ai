from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional, Union

from .utils import GenerationResult, get_tokenizer

PromptContext = Union[str, List[dict[str, str]]]


class BaseLLM(ABC):
    """LLM応答生成モジュールの抽象基底クラス。"""

    def __init__(self, model_name: str, system_prompt: str):
        """
        Args:
            model_name: モデル名（例：'gpt-4o-mini', 'gemma-2-27b', etc.）
            system_prompt: システムプロンプト（指定しない場合はデフォルト人格）
        """
        self._model_name = model_name
        self._system_prompt = system_prompt

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    def set_system_prompt(self, prompt: str):
        """必要に応じて人格や方針を変更できる（例：学長AI、教育者モードなど）"""
        self._system_prompt = prompt

    async def count_tokens(self, text: str) -> int:
        """モデル名に基づきトークナイザーを自動取得し、トークン数を算出"""
        tokenizer = get_tokenizer(self.model_name)
        return len(tokenizer(text))

    @abstractmethod
    def build_context(
        self,
        message: str,
        system_prompt: str,
        history: List[dict[str, str]],
    ) -> PromptContext:
        """履歴と発話を結合してプロンプトコンテキストを構築"""
        ...

    @abstractmethod
    async def _generate_impl(
        self,
        message: str,
        history: List[dict[str, str]],
        max_tokens: int,
        temperature: float,
        tool_calls: Optional[List[dict[str, str]]] = None,
    ) -> str:
        """内部的な生成処理本体。messageを入力に応答を返す。"""
        ...

    # ───────────────────────────────
    # generate（非ストリーミング）
    # ───────────────────────────────
    async def generate(
        self,
        message: str,
        history: Optional[List[dict[str, str]]] = None,
        tool_calls: Optional[List[dict[str, str]]] = None,
        *,
        token_count: bool = False,
        max_tokens: int = 150,
        temperature: float = 0.8,
    ) -> str | GenerationResult:
        """
        LLMによる全文（完了形）応答を返す。

        Args:
            message: 現在のユーザー発話
            history: 過去の会話履歴 [{"role": "user"/"assistant", "content": str}, ...]
            tool_calls: 関数呼び出しなどが必要な場合の指定
            token_count: True の場合はトークン数の情報も返す
        """

        # トークン数有りモード
        if token_count:
            prompt_tokens = await self.count_tokens(message)
            content = await self._generate_impl(message, history, tool_calls)
            completion_tokens = await self.count_tokens(content)
            return GenerationResult(
                content=content,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

        return await self._generate_impl(
            message, history, tool_calls, max_tokens, temperature
        )

    @abstractmethod
    async def stream_generate(
        self,
        message: str,
        history: Optional[List[dict[str, str]]] = None,
        tool_calls: Optional[List[dict[str, str]]] = None,
        max_tokens: int = 150,
        temperature: float = 0.8,
    ) -> AsyncIterator[str]:
        """トークンまたは文チャンクを ``async for`` で逐次返す。"""
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support streaming generation."
        )
