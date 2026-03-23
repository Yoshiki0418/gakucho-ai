import os
from typing import AsyncIterator

from agents import Agent, Runner, WebSearchTool
from app.prompts.president_persona import get_president_persona
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
        president_persona = get_president_persona()

        self.agent = Agent(
            name="PresidentAgent",
            model="gpt-5.2",
            instructions=f"""
                {president_persona}

                あなたは President ドメイン専門のエージェントです。
                上記で定義された大澤学長のペルソナとして、ユーザーからの質問に回答してください。

                【回答スタイル】
                - 説明は短く、分かりやすく、実用的に。
                - 少しユーモアを交えて親しみやすく。

                【ツール利用の方針】
                - WebSearchTool の使用は必要時のみ
                - 個人のプライバシーに紐づく検索は行わない
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
