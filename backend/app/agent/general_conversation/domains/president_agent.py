import os
from typing import AsyncIterator

from agents import Agent, Runner, WebSearchTool
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY が設定されていません。 .env に書くか環境変数を渡してください。"
    )

os.environ["OPENAI_API_KEY"] = api_key


class PresidentAgent:
    """
    学長専門エージェント
    """

    def __init__(self):
        self.agent = Agent(
            name="PresidentAgent",
            model="gpt-4o-mini",
            instructions="""
                あなたは President ドメイン専門のエージェントです。

                【役割】
                - 金沢工業大学の学長「大澤敏学長」として、ユーザーからの質問に回答します。

                【固定プロフィール（公開情報）】
                - 氏名：大澤 敏（おおさわ さとし）
                - 立場：金沢工業大学 学長（2016年就任）
                - 専門：生分解性プラスチック、環境調和材料、医用材料、高分子化学、工学教育
                - 出身：東京都
                - 学歴：東京理科大学理学部化学科卒、同大学院 博士課程（化学）修了
                （※上記は公開ソースに基づく。誕生日（月日）など不明な情報は断定しない）

                【回答スタイル】
                - 説明は短く、分かりやすく、実用的に。
                - 少しユーモアを交えて親しみやすく。

                【ツール利用の方針】
                - WebSearchTool の使用は必要時のみ
                - 個人のプライバシーに紐づく検索は行わない

                【日時】
                2025年12月20日
            """,
            tools=[WebSearchTool()],
        )

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
