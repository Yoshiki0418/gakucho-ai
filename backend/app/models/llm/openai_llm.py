import os
from typing import AsyncIterator, List, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI

from .base_llm import BaseLLM, PromptContext

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)
openai_streaming_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


class OpenAILLM(BaseLLM):
    """OpenAI Chat APIを利用したLLM実装クラス"""

    def __init__(
        self,
        system_prompt: str,
        model_name: str = "gpt-4o-mini",
    ):
        self._system_prompt = system_prompt
        self._model_name = model_name

    # ───────────────────────────────
    # コンテキスト構築
    # ───────────────────────────────
    def build_context(
        self,
        message: str,
        system_prompt: str,
        history: Optional[List[dict[str, str]]] = None,
    ) -> PromptContext:
        """
        OpenAI形式（messages形式）でコンテキストを構築する。
        """
        messages = [{"role": "system", "content": system_prompt}]
        if history is not None:
            messages += history
        messages.append({"role": "user", "content": message})

        return messages

    # ───────────────────────────────
    # 非ストリーミング生成
    # ───────────────────────────────
    async def _generate_impl(
        self,
        message: PromptContext,
        history: Optional[List[dict[str, str]]] = None,
        tool_calls: Optional[List[dict[str, str]]] = None,
        max_tokens: int = 150,
        temperature: float = 0.8,
    ) -> str:
        """OpenAIのChatCompletion APIを利用して応答を生成"""

        messages = self.build_context(message, self._system_prompt, history)

        print(messages)

        response = openai_client.chat.completions.create(
            model=self._model_name,
            messages=messages,
            tools=tool_calls,
            tool_choice="auto",
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return response.choices[0].message.content.strip()

    # ───────────────────────────────
    # ストリーミング生成
    # ───────────────────────────────
    async def stream_generate(
        self,
        message: str,
        history: Optional[List[dict[str, str]]] = None,
        tool_calls: Optional[List[dict[str, str]]] = None,
        max_tokens: int = 150,
        temperature: float = 0.8,
    ) -> AsyncIterator[str]:
        """OpenAI APIのストリームモードを利用して逐次出力"""

        messages = self.build_context(message, self._system_prompt, history, tool_calls)

        # OpenAI 非同期ストリーム
        stream = await openai_streaming_client.chat.completions.create(
            model=self._model_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
