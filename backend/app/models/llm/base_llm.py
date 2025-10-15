from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List, Optional, Union

from .utils import GenerationResult
from .utils import get_tokenizer

PromptContext = Union[str, List[Dict[str, str]]]

class BaseLLM(ABC):
    """LLM応答生成モジュールの抽象基底クラス。"""

    _model_name: str
    _system_prompt: str = (
        "あなたは金沢工業大学の学長です。"
        "常に相手の意図を正確に理解し、思いやりのある自然な言葉で説明します。"
        "ユーザーを生徒として話し、長すぎる説明は避け、テンポよく短めの発言を心がけてください。"
    )

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
        history: List[Dict[str, str]],
        tool_calls: Optional[List[Dict[str, str]]] = None,
    ) -> PromptContext:
        """履歴と発話を結合してプロンプトコンテキストを構築"""
        ...

    @abstractmethod
    async def _generate_impl(
        self,
        message: str,
        history: List[Dict[str, str]],
        tool_calls: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """内部的な生成処理本体。messageを入力に応答を返す。"""
        ...

    # ───────────────────────────────
    # generate（非ストリーミング）
    # ───────────────────────────────
    async def generate(
        self,
        message: str,
        history: List[Dict[str, str]],
        tool_calls: Optional[List[Dict[str, str]]] = None,
        *,
        token_count: bool = False,
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

        return await self._generate_impl(message, history, tool_calls)

    @abstractmethod
    async def stream_generate(
        self,
        message: str,
        history: List[Dict[str, str]],
        tool_calls: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncIterator[str]:
        """トークンまたは文チャンクを ``async for`` で逐次返す。"""
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support streaming generation."
        )