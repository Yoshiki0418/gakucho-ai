from typing import Any, AsyncIterator

from app.agent.modules import LLMDecisionClassifier
from app.models.llm import LocalLLM, OpenAILLM


class DialogueManager:
    """ローカルLLMとAPI LLMを併用できるハイブリッド対話マネージャ"""

    def __init__(self):
        self.local_llm = LocalLLM(
            model_name="lm-mini-1.5b", system_prompt="短文・自然な会話に特化"
        )
        self.api_llm = OpenAILLM(
            model_name="gpt-4o-mini", system_prompt="論理推論・Webブラウジング用"
        )
        self.decision_llm = LLMDecisionClassifier(model_name="gpt-4o-mini")

    # ==========================================================
    # Rule-based（従来型）
    # ==========================================================
    async def run_rule_based(
        self, user_input: str, context: dict[str, Any]
    ) -> AsyncIterator[str]:
        """
        手動またはルールベースでlocal/apiを切り替える。
        雑談や短文 → local、知識質問 → api。
        """
        classification = await self.decision_llm.classify_complexity(user_input)

        if "complex" in classification:
            async for chunk in self.api_llm.stream_generate(
                message=user_input,
                history=context.get("history", []),
            ):
                yield chunk
        else:
            async for chunk in self.local_llm.stream_generate(
                message=user_input,
                history=context.get("history", []),
            ):
                yield chunk

    # TODO: Function Callingベースの自動切り替えも実装？
