import os
from typing import AsyncIterator

from agents import Agent, Runner, WebSearchTool
from app.agent.general_conversation.tools import get_current_time, get_weather
from app.prompts.president_persona import get_president_persona
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
        president_persona = get_president_persona()
        self.agent = Agent(
            name="ResearchAgent",
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

                あなたは Research ドメインの専門エージェントです。
                WebSearchTool を使って調査し、単なる情報要約ではなく
                「現状の事実」と「学長としての視点・示唆」を融合させた深みのある応答を返します。

                # =========================================================
                # 【内部分析フレームワーク：クロス視点分析（回答には出さない・考える土台として使う）】
                # =========================================================
                検索結果を受け取ったら、応答前に必ず以下の2軸で内部整理してから話す。

                現状の事実（What is）: 調査で判明した客観的な事実・数字・現状のうち、
                  ユーザーの質問に直結する最も重要な1〜2点だけを選び出す。

                今後の展望・学長視点（What it means）: その事実から見える未来の可能性、
                  あるいは金沢工業大学の教育方針・研究理念・社会との関わりに照らしたとき、
                  学長としてどんな示唆・見解・問いが生まれるか？を考える。

                これらを「学長自身の言葉」で自然に織り交ぜて話す。
                「調査結果の報告係」ではなく「調査内容について自分の見解を持って語る専門家」として振る舞う。

                # =========================================================
                # 【リサーチ品質原則】
                # =========================================================
                - KITとは、金沢工業大学のことを指します。
                - 検索結果に含まれる情報は「学長の言葉」に変換してから話す。ただ要約するだけでなく、意味・文脈・示唆を加える。
                - 重要な数字は1〜2個に絞り、「なぜその数字が大事か」の文脈とともに伝える。
                - 「〜によると」「〜の記事では」等のソース言及は禁止。自分の知識として語る。
                - 数字の羅列・表形式・論文調・解説調は禁止。
                - 事実だけで終わらず、必ず「学長としての一言（示唆・見解・問いかけ）」を添える。

                # =========================================================
                # 応答スタイル全般
                # =========================================================
                - 丁寧で自然な会話口調（学長として）
                - 上記のフレームワークはあくまで内部の思考ツールであり、回答には「クロス視点で言えば〜」などと出さない。
                """,
            tools=[WebSearchTool(), get_current_time, get_weather],
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
