from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from app.models.llm import BaseLLM
from app.rag.retriever import Retriever


class RAGModule:
    """
    Retrieval-Augmented Generation を担当するモジュール。
    - Retriever を用いた検索
    - プロンプトテンプレートの読み込み
    - LLM へ渡す最終プロンプトの構築

    LLM の推論部分は上位レイヤー（AgentManager）が呼び出す想定。
    """

    def __init__(
        self,
        retriever: Retriever,
        llm: BaseLLM,
        prompt_dir: str = "app/prompts/rag",
        default_prompt_name: str = "default.md",
        max_tokens: int = 200,
        temperature: float = 0.7,
    ):
        self.retriever = retriever
        self.prompt_dir = Path(prompt_dir)
        self.default_prompt_name = default_prompt_name
        self.llm = llm
        self.max_tokens = max_tokens
        self.temperature = temperature

    # ----------------------------------------------------------
    # プロンプトテンプレート読込
    # ----------------------------------------------------------
    def load_prompt(self, name: Optional[str] = None) -> str:
        """
        指定されたテンプレート名 (md / txt) をロード。
        デフォルト: default.md
        """
        filename = name or self.default_prompt_name
        path = self.prompt_dir / filename

        if not path.exists():
            raise FileNotFoundError(f"Prompt template not found: {path}")

        return path.read_text(encoding="utf-8")

    # ----------------------------------------------------------
    # プロンプト生成
    # ----------------------------------------------------------
    def build_prompt(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        template_name: Optional[str] = None,
    ) -> str:
        """
        LLM に渡すためのプロンプトを構築する。
        """
        template = self.load_prompt(template_name)

        # --- コンテキスト整形 ---
        def format_doc(i: int, d: Dict[str, Any]) -> str:
            text = f"[{i+1}] (score={d['similarity']:.3f})\n{d['context']}"
            if d.get("source_url"):
                text += f"\n参考URL: {d['source_url']}"
            return text

        context_text = "\n\n".join(
            [format_doc(i, d) for i, d in enumerate(retrieved_docs)]
        )

        # --- テンプレート置換 ---
        prompt = template.replace("{{query}}", query)
        prompt = prompt.replace("{{context}}", context_text)

        print(f"\n[DEBUG RAG] ===================")
        print(f"Retrieved Context:\n{context_text}")
        print(f"=================================\n")

        return prompt

    async def run(
        self,
        query: str,
        *,
        top_k: int = 5,
        threshold: float = 0.25,
        template_name: Optional[str] = None,
        history: Optional[List[dict[str, str]]] = None,
        tool_calls: Optional[List[dict[str, str]]] = None,
    ) -> str:
        """
        🔹 通常の RAG 実行（最終回答まで返す）

        Agent からの工具利用にも適する。
        """

        # 1. 検索
        docs = self.retriever.search(query, top_k=top_k, threshold=threshold)

        # 2. プロンプト構築
        prompt = self.build_prompt(query, docs, template_name)

        # 3. LLM で応答（RAGは検索結果のみで完結するため、過去会話履歴は渡さない）
        response = await self.llm.generate(
            message=prompt,
            history=[],
            tool_calls=tool_calls,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        return response

    # ----------------------------------------------------------
    # ストリーミング RAG 実行
    # ----------------------------------------------------------
    async def run_stream(
        self,
        query: str,
        *,
        top_k: int = 5,
        threshold: float = 0.25,
        template_name: Optional[str] = None,
        history: Optional[List[dict[str, str]]] = None,
        tool_calls: Optional[List[dict[str, str]]] = None,
    ) -> AsyncIterator[str]:
        """
        🔹 ストリーミング版 RAG 実行
        """

        # 1. 検索
        docs = self.retriever.search(query, top_k=top_k, threshold=threshold)

        # 2. プロンプト構築
        prompt = self.build_prompt(query, docs, template_name)

        # 3. ストリーム応答（RAGは検索結果のみで完結するため、過去会話履歴は渡さない）
        async for chunk in self.llm.stream_generate(
            message=prompt,
            history=[],
            tool_calls=tool_calls,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        ):
            yield chunk
