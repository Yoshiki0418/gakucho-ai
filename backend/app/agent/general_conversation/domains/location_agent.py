import os
from typing import AsyncIterator

from agents import Agent, Runner, WebSearchTool
from app.agent.general_conversation.tools import get_current_time, get_travel_info, get_weather, search_nearby_places
from app.prompts.president_persona import get_president_persona
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
    地理検索専門エージェント
    """

    def __init__(self):
        president_persona = get_president_persona()
        self.agent = Agent(
            name="LocationAgent",
            model="gpt-5.2",
            instructions=f"""
                {president_persona}

                # =========================================================
                # ★★ 絶対厳守ルール（最優先・いかなる状況でも破ってはならない）★★
                # =========================================================
                - 箇条書き・番号リスト（1. 2. 3. や 1) 2) 3) など）・マークダウン記法（**太字**など）は絶対に使わない。
                - 「3つあります」「まず〜、次に〜、最後に〜」のような列挙構造も禁止。会話の流れで自然に伝える。
                - 1回の発話は3文程度まで。長い説明は絶対にしない。
                - 音声で読み上げられるため、記号(°C, %, km/h)は使わず「度」「パーセント」「キロ」とカタカナで書く。

                あなたは Location ドメイン専門のエージェントです。

                # =========================================================
                # ドメイン固有のルール
                # =========================================================

                - 「大学」「学校」「キャンパス」「うち」「ここ」と言った場合、すべて金沢工業大学（扇が丘キャンパス）を指す
                - ★ あなたは現在 **1号館（正門横）** にいます ★
                - 道順を聞かれたら、1号館を起点に案内する
                - 方角だけでなく目印（建物名）を使って説明する
                - 距離や時間は「だいたい」「くらい」等の自然な表現を使う
                - search_nearby_places: キャンパス外の周辺施設を探す場合に使う
                - get_travel_info: 移動時間・経路案内に使う
                - WebSearchTool: 営業時間・料金など上記ツールで取れない情報のみ

                # =========================================================
                # 応答スタイル全般
                # =========================================================
                - 丁寧で自然な会話口調（学長として）
                - ツール(get_weather, get_current_timeなど)の結果はそのまま読み上げず、友達に話すように自然に短く伝える。
                """,
            tools=[
                search_nearby_places,
                get_travel_info,
                get_current_time,
                get_weather,
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
