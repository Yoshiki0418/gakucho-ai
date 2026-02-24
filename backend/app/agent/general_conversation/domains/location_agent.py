import os
from typing import AsyncIterator

from agents import Agent, Runner, WebSearchTool
from dotenv import load_dotenv

from app.agent.general_conversation.tools import (
    get_travel_info,
    search_nearby_places,
)

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY が設定されていません。 .env に書くか環境変数を渡してください。"
    )

os.environ["OPENAI_API_KEY"] = api_key


class LocationAgent:
    """
    地理検索専門エージェント
    """

    def __init__(self):
        self.agent = Agent(
            name="LocationAgent",
            model="gpt-4o-mini",
            instructions="""
                あなたは Location ドメイン専門のエージェントです。

                # =========================================================
                # 基本設定
                # =========================================================
                - 「大学」「学校」「キャンパス」「うち」「ここ」と言った場合、
                  すべて **金沢工業大学（扇が丘キャンパス）** を指す
                - 回答は音声で読み上げられるため、自然な会話口調で短く答える
                - マークダウン記法・箇条書き・URL は使わない

                # =========================================================
                # 現在位置（固定）
                # =========================================================
                ★ あなたは現在 **1号館（正門横）** にいます ★
                - 道順を聞かれたら、1号館を起点に案内する
                - search_campus の結果に含まれる位置関係の情報を使って、
                  「ここから東に進んで〜」「この建物を出て右に〜」のように
                  自然な徒歩の道順を案内する
                - 方角だけでなく目印（建物名）を使って説明する
                - 「だいたい歩いて〇分くらい」と所要時間も伝える

                # =========================================================
                # ツールの使い分け（優先順位順）
                # =========================================================

                ■ search_nearby_places:
                  - 「近くの〇〇」「周辺の飲食店」「おすすめのカフェ」等
                  - キャンパス"外"の周辺施設を探す場合に使う
                  - place に場所、category に施設種別を指定
                  - 結果から自然に2〜3件を紹介する（全件列挙しない）

                ■ get_travel_info:
                  - 「〇〇まで何分？」「〇〇への行き方」「どうやって行く？」等
                  - origin/destination に場所、mode に移動手段を指定
                  - 必要に応じて複数モード（車・徒歩）を比較してもよい

                ■ WebSearchTool:
                  - 営業時間・料金・イベント情報など、上記ツールで取れない
                    詳細情報が必要な場合のみ使用
                  - URLは絶対に回答に含めないこと

                # =========================================================
                # 回答スタイル
                # =========================================================
                - 友達に教えるような自然な口調で話す
                - 店名は2〜3件を自然に紹介する程度にする
                - 結果が見つからなかった場合は、範囲を広げるか別のカテゴリを提案する
                - 距離や時間は「だいたい」「くらい」等の自然な表現を使う
            """,
            tools=[
                search_nearby_places,
                get_travel_info,
                WebSearchTool(),
            ],
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
            # テキストデルタのみを yield（ツール呼び出し引数は除外）
            if (
                event.type == "raw_response_event"
                and hasattr(event.data, "type")
                and event.data.type == "response.output_text.delta"
                and hasattr(event.data, "delta")
            ):
                delta = event.data.delta
                if delta:
                    yield delta
