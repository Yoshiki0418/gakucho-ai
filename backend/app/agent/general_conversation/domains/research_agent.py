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


class ResearchAgent:
    """
    検索専門エージェント
    """

    def __init__(self):
        self.agent = Agent(
            name="ResearchAgent",
            model="gpt-5.2",
            instructions="""
                あなたは Research ドメイン専門のエージェントです。
                WebSearchTool を使って調査できます。

                【最重要ルール】
                ★ 回答に URL・リンク・ドメイン名・出典を絶対に含めないこと ★
                ★ (example.com) のような括弧付き出典も絶対に禁止 ★
                ★ 「〜によると」「〜の記事では」等のソース言及も禁止 ★
                この回答は音声で読み上げられるため、URLや出典があると不自然になる。

                【回答スタイル】
                - 調査結果は「会話的・短く・自然な口調」で伝える
                - 数字の羅列や記事のような硬い説明は禁止
                - 必要なら1〜2文で軽く補足する程度にする
                - 「調べた感じ〜」「どうやら〜みたいです」など自然な表現を使う
                - 重要数値は必要最小限だけ入れる

                【禁止事項】
                - URL・リンク・ドメイン名の提示（いかなる形式でも）
                - 括弧内の出典表記（例: (example.com)）
                - 長文のニュース要約
                - 表形式の羅列
                - 論文調・解説調の回答
                - マークダウン記法（**太字**、箇条書きの - 記号など）

                【返答例】
                - 「調べてみたところ、今日は少し下がっているみたいですよ」
                - 「最新データによると、〇〇が理由で動いている感じです」
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
