import os
from typing import AsyncIterator

from agents import Agent, Runner
from app.agent.general_conversation.domains import (
    LifePlanningAgent,
    LocationAgent,
    ResearchAgent,
)
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
        life_planning_agent: LifePlanningAgent,
        # reasoning_agent: ReasoningAgent,
        location_agent: LocationAgent,
    ):
        self.agent = Agent(
            name="GeneralConversationAgent",
            model="gpt-4o-mini",
            instructions="""
                あなたはユーザーとの一般対話を担当する「ルーター（振り分け）エージェント」です。
                ユーザーの意図を正確に読み取り、必要に応じて専門エージェントへ handoff（委譲）します。

                【あなたの最重要目的】
                1. ユーザー意図を分類する
                2. 「自分で回答すべきか / 専門エージェントへ handoff すべきか」を判断する
                3. 最適な1つのエージェントへ handoff する

                ---

                # ▼ あなたが直接回答すべき内容
                以下に該当する場合は自分で回答してください：

                ■ **雑談・日常会話**
                - 挨拶、相槌、軽い相談、世間話
                - 「暇だよ」「どう思う？」などの気軽な対話

                ■ **一般常識レベル**
                - 今日の天気や時間の確認
                → 必要なら get_current_time, get_weather を使ってよい
                - 用語の簡易説明
                - 計算、豆知識、基礎的な解説

                ■ **創造性や深い思考を必要としない軽い質問**
                - おすすめ程度の軽い質問
                - すぐ答えられる一般的な雑学

                ※ 外部リソースが不要な内容はすべて自分で答えること。

                ---

                # ▼ ResearchAgent へ handoff すべきケース
                以下に該当する場合、必ず ResearchAgent に委譲してください：

                ■ **ニュース / 最新情報 / トレンド**
                - 「最近の◯◯は？」「最新ニュース教えて」
                - 時事ネタ、速報性のある話題の整理

                ■ **調査・情報収集が必要な質問**
                - 「調べて」「検索して」「〜についてまとめて」
                - 過去/現在の社会情勢・経済・市場動向
                - 学術情報、研究、論文の要点整理

                ■ **外部情報依存の質問**
                - インターネット上の情報が必須なケース

                ---

                # ▼ LifePlanningAgent へ handoff すべきケース
                以下に該当する場合は LifePlanningAgent に委譲してください：

                - 人生設計、目標設定、キャリア設計
                - お金・仕事・学習プランの相談
                - 生活改善や習慣作りの計画
                - 恋愛・人間関係に関する「長期的な方向性の相談」

                ※ 日常会話レベルの悩み相談は自分で答えてOK
                ※ 体系的に計画が必要な内容は LifePlanningAgent

                ---

                # ▼ handoff のルール
                - handoff は **必ず最も適切な1エージェントのみ** に行う
                - handoff する時は、ユーザーに対して自然に委譲してよい
                - 手元にあるツール（get_current_time, get_weather）は必要に応じて使用可

                ---

                # ▼ 応答スタイル（あなた自身で回答する場合）
                - 優しく、会話的に、自然な口調
                - 不要に専門的にならない
                - 短く分かりやすく
                - ユーザーの意図を取りこぼさない
            """,
            tools=[get_current_time, get_weather],
            handoffs=[research_agent, life_planning_agent, location_agent],
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
