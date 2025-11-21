import os
from typing import AsyncIterator

from agents import Agent, Runner
from app.agent.general_conversation.tools import get_current_time, get_weather
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY が設定されていません。 .env に書くか環境変数を渡してください。"
    )

os.environ["OPENAI_API_KEY"] = api_key


class GeneralConversationAgent:
    """
    日常対話ルーターエージェント。挨拶・雑談・一般常識には対応し、
    専門領域には適切なドメインエージェントに handoff します。
    """

    def __init__(
        self,
        # research_agent: ResearchAgent,
        # reasoning_agent: ReasoningAgent,
        # location_agent: LocationAgent,
    ):
        self.agent = Agent(
            name="GeneralConversationAgent",
            model="gpt-4o-mini",
            instructions="""
                あなたはユーザーとの日常対話を担当する一般対話ルーターエージェントです。

                - 挨拶・軽い雑談・世間話は自分で直接答える
                - 一般常識レベルの質問（今日の天気？今何時？など）も自分で答えてよい
                - しかし専門領域（研究・文章・推論・位置情報・学内情報）が必要な場合は
                適切なドメインエージェントに handoff する
                - 迷ったら ReasoningAgent を優先する
            """,
            tools=[get_current_time, get_weather],
            # handoffs=[research_agent, reasoning_agent, location_agent],
        )
        # self.domain_agents: dict[str, Agent] = {
        #     "research": research_agent,
        #     "reasoning": reasoning_agent,
        #     "location": location_agent,
        # }

    async def generate(self, user_id: str, message: str, **kwargs) -> str:
        # 前処理ログ等を入れるならここ
        result = await Runner.run(self.agent, message)
        return result.final_output

    async def stream_generate(
        self, user_id: str, message: str, **kwargs
    ) -> AsyncIterator[str]:
        """
        ストリーミング応答を返すメソッド。
        LLMの生成途中のチャンクを逐次返します。
        """
        # ストリームモードで実行
        stream_result = Runner.run_streamed(self.agent, message)
        async for event in stream_result.stream_events():
            # raw_response_event としてテキストデルタがある場合
            if event.type == "raw_response_event" and hasattr(event.data, "delta"):
                yield event.data.delta
