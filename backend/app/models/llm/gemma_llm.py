import asyncio
import re
from typing import AsyncIterator, List, Optional, Union

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TextIteratorStreamer,
    pipeline,
)

from . import BaseLLM

PromptContext = Union[str, List[dict[str, str]]]


class GemmaLLM(BaseLLM):
    """
    google/gemma-2-2b-jpn-it をローカル実行する LLM 実装。
    - transformers の text-generation pipeline を利用
    - BaseLLM を継承して generate / stream_generate を提供
    """

    def __init__(
        self,
        model_name: str = "google/gemma-2-2b-jpn-it",
        system_prompt: str = """
あなたは「簡潔に話す日本語アシスタント」です。

【重要ルール】
- あなたは「超簡潔に話すアシスタント」です。
- 返答は必ず1〜2文に収めてください。
- 説明や背景を追加してはいけません。
- 箇条書きは禁止です。
- 直接答えてください。
""",
        device: str | int | None = None,
    ):
        super().__init__(model_name=model_name, system_prompt=system_prompt)

        if device is None:
            if torch.cuda.is_available():
                device = 0  # first GPU
            else:
                device = "cpu"

        # HF トークナイザ（トークンカウント用）
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)

        self._model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16,
            device_map="auto",
        )

        # text-generation pipeline を構築（bfloat16 + GPU前提）
        self._pipe = pipeline(
            "text-generation",
            model=model_name,
            model_kwargs={"torch_dtype": torch.bfloat16},
            device=device,
        )

        self.device = device

    # ----------------------------------------------------------
    # トークンカウント
    # ----------------------------------------------------------
    async def count_tokens(self, text: str) -> int:
        return len(self._tokenizer.encode(text))

    # ----------------------------------------------------------
    # コンテキスト構築
    # ----------------------------------------------------------
    def build_context(
        self,
        message: str,
        system_prompt: str,
        history: List[dict[str, str]],
        tool_calls: Optional[List[dict[str, str]]] = None,
    ) -> PromptContext:
        """
        system_prompt + 過去履歴 + 現在のユーザー発話 を1つのテキストにまとめる。
        Gemmaはインストラクションフォーマットもあるが、まずはシンプルな日本語プロンプトとして構築。
        """
        lines: List[str] = []

        # システムプロンプト
        if system_prompt:
            lines.append(f"[システム]\n{system_prompt}\n")

        # 履歴
        for turn in history:
            role = turn.get("role", "user")
            content = turn.get("content", "")

            if role == "assistant":
                prefix = "アシスタント"
            elif role == "system":
                prefix = "システム"
            else:
                prefix = "ユーザー"

            lines.append(f"[{prefix}]\n{content}\n")

        # 現在のユーザー発話
        lines.append(f"[ユーザー]\n{message}\n")
        lines.append("[アシスタント]\n")

        return "\n".join(lines)

    # ----------------------------------------------------------
    # 内部生成処理
    # ----------------------------------------------------------
    async def _call_pipeline(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> str:
        """
        transformers の pipeline をスレッドプールで実行し、イベントループをブロックしないようにする。
        """
        loop = asyncio.get_running_loop()

        def _sync_call() -> str:
            outputs = self._pipe(
                prompt,
                return_full_text=False,
                max_new_tokens=max_tokens,
                do_sample=temperature > 0,
                temperature=temperature,
                top_p=top_p,
                pad_token_id=self._tokenizer.eos_token_id,
            )
            assistant_response = outputs[0]["generated_text"].strip()

            assistant_response = re.sub(r"\*\*+", "", assistant_response)

            return assistant_response.strip()

        return await loop.run_in_executor(None, _sync_call)

    async def _generate_impl(
        self,
        message: str,
        history: List[dict[str, str]],
        tool_calls: Optional[List[dict[str, str]]] = None,
        max_tokens: int = 256,
        temperature: float = 0.3,
        top_p: float = 0.8,
    ) -> str:

        history = history or []

        prompt = self.build_context(
            message=message,
            system_prompt=self.system_prompt,
            history=history,
            tool_calls=tool_calls,
        )
        return await self._call_pipeline(prompt, max_tokens, temperature, top_p)

    # ============================================================
    #   ストリーミング生成
    # ============================================================
    async def stream_generate(
        self,
        message: str,
        history: Optional[List[dict[str, str]]] = None,
        tool_calls: Optional[List[dict[str, str]]] = None,
        max_tokens: int = 150,
        temperature: float = 0.3,
        top_p: float = 0.8,
    ) -> AsyncIterator[str]:

        history = history or []

        # ---- プロンプト構築 ----
        prompt = self.build_context(
            message=message,
            system_prompt=self.system_prompt,
            history=history,
            tool_calls=tool_calls,
        )

        # ---- tokenizer ----
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self.device)

        # ---- streamer ----
        streamer = TextIteratorStreamer(
            self._tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
        )
        import threading

        # ---- バックグラウンドスレッドで generate 実行 ----
        def _run():
            self._model.generate(
                **inputs,
                streamer=streamer,
                max_new_tokens=max_tokens,
                do_sample=temperature > 0,
                temperature=temperature,
                top_p=top_p,
            )

        thread = threading.Thread(target=_run)
        thread.start()

        # ---- ストリームとして逐次返す ----
        for new_text in streamer:
            new_text = re.sub(r"\*\*+", "", new_text)
            yield new_text
