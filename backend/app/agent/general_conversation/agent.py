import os
from typing import AsyncIterator

from agents import Agent, Runner
from app.agent.general_conversation.domains import ResearchAgent
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
        research_agent: ResearchAgent,
        # reasoning_agent: ReasoningAgent,
        # location_agent: LocationAgent,
    ):
        self.agent = Agent(
            name="GeneralConversationAgent",
            model="gpt-4o-mini",
            instructions="""
                あなたはユーザーとの日常対話を担当する一般対話ルーターエージェントです。

                【あなたの目的】
                ユーザーの入力を理解し、以下の基準に従って
                ・自分で回答する
                ・適切な専門エージェントに handoff する
                を判断します。

                【あなたが直接回答すべき内容】
                - 挨拶・雑談・軽い世間話
                - 一般常識レベルの質問（天気 / 時刻 / 身近な情報）
                - 工夫なしで答えられる簡易質問

                【ResearchAgent に handoff すべき内容】
                以下のいずれかに該当する場合、ResearchAgent へ handoff する：
                - ニュース / トレンド / 最新情報に関する質問
                - データや事実を調査して答える必要がある場合
                - 「調べて」「検索して」「まとめて」のような調査要求
                - 過去/現在/未来の社会情勢・市場分析・政治・経済の情報整理
                - 論文・研究・学術的情報の要約や比較
                - 外部リソースを参照しないと回答が困難な内容

                【その他のドメイン】
                - 複雑な思考を伴う質問 → ReasoningAgent
                - 文章の作成・添削 → WritingAgent
                - 創造的なアイデア生成 → CreativeAgent
                - ライフプラン相談 → LifePlanningAgent

                【ルール】
                - どの分類にも迷ったら ReasoningAgent に handoff する
                - handoff を行う際は最も適切なエージェントを1つ選ぶ
            """,
            tools=[get_current_time, get_weather],
            handoffs=[research_agent],
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
