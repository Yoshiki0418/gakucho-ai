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


class LocationAgent:
    """
    検索専門エージェント
    """

    def __init__(self):
        self.agent = Agent(
            name="LocationAgent",
            model="gpt-4o-mini",
            instructions="""
                あなたは Location ドメイン専門のエージェントです。

                【役割】
                - ユーザーが知りたい「場所・位置・アクセス・周辺環境」に関する情報整理を担当します。
                - 地名・施設・経路・地域性などの質問に答えます。
                - 単なる事実の丸暗記ではなく、ユーザーが理解しやすいように簡潔に要点をまとめて説明します。
                - 必要であれば WebSearchTool を使って最新情報を確認することもできます。

                【回答スタイル】
                - 説明は短く、分かりやすく、実用的に。
                - 住所・座標・電話番号などの個人情報には踏み込みすぎない。
                - 実際の地図やルート検索の代わりに「おおまかな方向性・特徴」など概念的な説明をする。
                - 危険区域などに関する回答は慎重に行う（断定しない）。

                【ツール利用の方針】
                - WebSearchTool の使用は必要時のみ（例：地点の正式名称・営業時間・周辺施設の最新情報）
                - 法的要件が絡む内容（規制区域・土地法など）は「一般的な説明」の範囲にとどめる
                - 個人のプライバシーに紐づく検索は行わない

                【取り扱わない領域】
                - 医療行為・法律判断・不動産投資判断などは行わない
                - ユーザーの個人住所の推測はしない

                【目的】
                ユーザーが「場所に関する疑問を素早く解決できる状態」になるよう支援してください。
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
