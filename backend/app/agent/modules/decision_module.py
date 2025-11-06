# agent/decision_manager.py
from __future__ import annotations

from typing import Any, Dict, Optional

from app.models.llm import OpenAILLM


class DecisionManager:
    """ユーザー入力に基づき、実行すべき処理を決定する中核クラス"""

    def __init__(self) -> None:
        # --- サブマネージャの初期化 ---
        self._build_llm()

    def _build_llm(self) -> None:
        """LLMを初期化"""
        system_prompt = (
            "あなたはユーザー発話の意図を解釈する専門家です。"
            "ユーザーの意図を適切に分類してください。"
        )
        model_name = "gpt-4o-mini"

        self.llm = OpenAILLM(
            model_name=model_name,
            system_prompt=system_prompt,
        )

    # ==========================================================
    # メイン処理
    # ==========================================================
    async def decide(
        self, user_input: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        ユーザー入力を受け取り、RAGまたは通常対話を選択して応答を生成する。
        """
        # --- Intent分類 ---
        intent = await self._analyze_intent(user_input, context)
        print(f"[DecisionManager] Detected intent: {intent}")

        return intent

    # ==========================================================
    # LLMベースの意図分類
    # ==========================================================
    async def _analyze_intent(
        self, user_input: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        LLMを用いた意図分類。
        入力文の意味に基づいて "rag" または "dialogue" を推定する。
        """
        prompt = f"""
        あなたは大学内AIアシスタントです。
        以下のユーザー発話が「学内情報」に関する質問かどうかを判定してください。

        ### 学内情報の例
        - 授業・講義・教員・学科・研究室・施設（例：図書館、学食、体育館）
        - イベント・スケジュール・履修登録・奨学金・学生支援・アクセス案内
        - 大学名（金沢工業大学、KIT）に関する話題
        - 学内システム（KITナビ、ポータル、Moodleなど）

        ### ルール
        - 上記のような「学内関連情報」を尋ねている場合は "rag"
        - 挨拶、雑談、感想、AIへの意見などは "dialogue"
        - 出力は "rag" または "dialogue" のどちらか一語のみ

        ユーザー発話: 「{user_input}」
        """

        response = await self.llm.generate(prompt)

        print(response)

        if "rag" in response:
            return "rag"
        return "dialogue"
