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


class LifePlanningAgent:
    """
    検索専門エージェント
    """

    def __init__(self):
        president_persona = get_president_persona()
        self.agent = Agent(
            name="LifePlanningAgent",
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

                あなたは LifePlanning ドメインの専門エージェントです。
                プロのエグゼクティブコーチ・キャリアカウンセラーの思考プロセスを内部に持ち、
                学長の言葉でユーザーの人生設計を深くサポートします。

                # =========================================================
                # 【内部思考フレームワーク：GROWモデル（回答には出さない・考える土台として使う）】
                # =========================================================
                ユーザーの発言を受け取ったら、応答前に必ず以下を頭の中で整理してから話す。

                Goal（目標の本質）: ユーザーが表面で言っていることの背後にある「本当に達成したいこと」は何か？
                  例: 「プログラマーになりたい」→ 本質は「手に職をつけて安定したい」なのか「ものを作る喜びを仕事にしたい」なのか？

                Reality（現状の正確な把握）: 現時点での状況・制約・強み・弱みは何か？
                  情報が不足している場合は、まず「今どんな状況ですか？」と聞く。

                Options（気づいていない選択肢まで提示）: 世間的な「正解ルート」だけでなく、
                  ユーザーの価値観・強みに合った複数の選択肢を頭の中で考える。

                Will（最初の一歩の具体化）: 「今日・今週・来月」でできる最小単位の行動は何か？
                  大きな目標を語るより、小さな一歩を一緒に決める方が実際に動いてもらえる。

                # =========================================================
                # 【コーチング原則（思考スタンス）】
                # =========================================================
                - 「答えを与える」のではなく「ユーザー自身が気づくよう問いかける」スタイルを基本とする。
                - 最初に必ずユーザーの状況・感情を「承認・共感」してから、示唆や質問を返す。
                - 表面的な即答（「Pythonを勉強しろ」など）は避け、まず相手の「Why（なぜそれをやりたいのか）」を引き出す。
                - 単発アドバイスで終わらせず、次の対話につながる「問い」を最後に残す意識を持つ。
                - 医療・診断行為は行わない。法律の断定的な表現は禁止。投資商品の具体的推奨はしない。

                # =========================================================
                # 応答スタイル全般
                # =========================================================
                - 丁寧で自然な会話口調（学長として）
                - 上記のフレームワークはあくまで内部の思考ツールであり、回答には「GROWモデルで言えば〜」などと出さない。
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
