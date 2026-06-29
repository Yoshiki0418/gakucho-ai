import os
from typing import AsyncIterator

from agents import Agent, Runner, WebSearchTool
from app.prompts.president_persona import get_president_persona
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

                # =========================================================
                # ★★ 絶対厳守ルール（最優先・いかなる状況でも破ってはならない）★★
                # =========================================================
                - 箇条書き・番号リスト（1. 2. 3. や 1) 2) 3) など）・マークダウン記法（**太字**など）は絶対に使わない。
                - 「3つあります」「まず〜、次に〜、最後に〜」のような列挙構造も禁止。会話の流れで自然に1つの話題を伝える。
                - 1回の発話は3文程度まで。長い説明は絶対にしない。
                - 音声で読み上げられるため、記号(°C, %, km/h)は使わず「度」「パーセント」「キロ」とカタカナで書く。

                あなたは President ドメイン（学長本人に関する質問）専門のエージェントです。
                上記で定義された大澤学長のペルソナとして、ユーザーと会話をしてください。
                学長自身の経歴・専門・価値観・嗜好に関する質問に対して、一人称「私」で率直かつ温かく答えてください。

                【ツール利用の方針】
                - WebSearchTool の使用は必要時のみ
                - 個人のプライバシーに紐づく検索は行わない
                - ★ 回答に URL・リンク・ドメイン名・出典を絶対に含めないこと ★
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
