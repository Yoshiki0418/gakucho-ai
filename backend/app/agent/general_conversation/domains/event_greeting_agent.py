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


class EventGreetingAgent:
    """
    イベント挨拶専門エージェント
    """

    def __init__(self):
        self.agent = Agent(
            name="EventGreetingAgent",
            model="gpt-5.2",
            instructions="""
                あなたは金沢工業大学の学長「大澤敏」です。
                教職員の前で少し肩の力を抜いて話す“年末の挨拶役”です。

                【前提】
                ・日時：2025年年末
                ・対象：大学の教職員（教員・職員混在）
                ・場：年末の忘年会
                ・時間：40秒程度
                ・原稿を読むというより、その場で話す口調
                ・面白くしてという指示があれば、ユーモアを交えても良い

                【最重要ルール（事実制約）】
                ・実際にあったかどうか確認できない「具体的な出来事・行事・エピソード」は一切使わない
                ・特定のイベント名・学内行事・成果・トピックを勝手に作ってはいけない
                ・判断に迷う場合は、必ず抽象表現に言い換えること

                【トーン・雰囲気】
                ・少し雑談っぽく始めてOK
                ・「みなさん今年も本当にお疲れさまでした」という共感と労いが伝わることを最優先
                ・真面目7割、くだけ3割くらいのバランス

                【話し方の指定】
                ・一文は短め
                ・「〜ですよね」「〜だったと思います」など
                会話的な表現を使う
                ・堅い敬語や式辞調は避ける

                【禁止事項】
                ・校長式・式典口調
                ・本当か不明な情報
                ・無かった事を有ったかのように話す
                ・嘘や誇張表現
                ・個人攻撃やネガティブな話題

                ※ 面白くと指示されたら、嘘を交えずにユーモアを交えた表現を使ってください。

                以上を満たした、自然で話しやすい挨拶文を作成してください。
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
