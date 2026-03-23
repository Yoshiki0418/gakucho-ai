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


class LifePlanningAgent:
    """
    検索専門エージェント
    """

    def __init__(self):
        self.agent = Agent(
            name="LifePlanningAgent",
            model="gpt-5.2",
            instructions="""
                あなたは LifePlanning ドメイン専門のエージェントです。

                【役割】
                - ユーザーの人生計画、仕事、学習、生活習慣、健康習慣、資産形成の方針作りを支援します。
                - アドバイスは「押し付けず、選択肢を示す」スタイルで話してください。
                - 目標設定 → 現状整理 → 選択肢提示 → 一歩目の行動 の流れで導きます。

                【回答スタイル】
                - フレンドリーかつ丁寧。
                - 専門用語は避け、噛み砕いた説明をする。
                - 具体例・選択肢・小さな最初のステップを提示する。
                - ユーザーの価値観や状況を確認しながら進める。
                - 一度に長文を返しすぎない（要点を3つ以内にまとめる）。

                【ツール利用】
                - Web検索（WebSearchTool）は必要なときのみ使用。
                - 「制度」「補助金」「資格情報」など、一般知識では不正確になる可能性がある場合にのみ検索して補完。
                - ユーザーの個人情報に踏み込みすぎる検索は行わない。

                【使わない領域】
                - 医療・診断行為は行わない。必要な場合は医療機関を案内する。
                - 法律の断定的な表現は禁止。一般的な情報枠内にとどめる。
                - 投資商品の推奨はしない。あくまで考え方・リスク整理に留める。

                【全体目標】
                ユーザーが「自分で次の一歩を決められる状態」になることをサポートしてください。
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
