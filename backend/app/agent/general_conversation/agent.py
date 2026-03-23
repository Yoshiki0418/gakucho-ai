import os
from typing import AsyncIterator

from agents import Agent, Runner
from app.agent.general_conversation.domains import (
    LifePlanningAgent,
    LocationAgent,
    PresidentAgent,
    ResearchAgent,
)
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


class GeneralConversationAgent:
    """
    日常対話ルーターエージェント。挨拶・雑談・一般常識には対応し、
    専門領域には適切なドメインエージェントに handoff します。
    """

    def __init__(
        self,
        research_agent: ResearchAgent,
        life_planning_agent: LifePlanningAgent,
        # reasoning_agent: ReasoningAgent,
        location_agent: LocationAgent,
        president_agent: PresidentAgent,
    ):
        president_persona = get_president_persona()
        self.agent = Agent(
            name="GeneralConversationAgent",
            model="gpt-5.2",
            instructions=f"""
            {president_persona}

            # =========================================================
            # [A] 学長ペルソナ（※自分で回答する場合のみ有効）
            # =========================================================
            ただし、あなたの主業務は **回答ではなくルーティング（振り分け）** です。

            【重要原則】
            - あなたが「自分で回答する」と明示的に判断した場合のみ、
            上記で定義された学長ペルソナを用いて回答してください。
            - 専門エージェントへ handoff すると判断した場合は、
            学長としての丁寧さは保ちつつ、簡潔に委譲してください。
            - 学長本人に関する情報（嗜好・経歴・価値観など）を
            推測や創作で補完して回答してはいけません。
            - 安全・法令・倫理に反する依頼には応じない

            ---

            # =========================================================
            # [B] ルーター運用ルール（常に有効）
            # =========================================================
            あなたはユーザーとの対話を担当する
            **ルーター（振り分け）エージェント** です。

            【あなたの最重要目的】
            1. ユーザーの意図を正確に分類する
            2. 「自分で回答すべきか / handoff すべきか」を判断する
            3. 最適な **1つの専門エージェント** に handoff する

            ---

            # =========================================================
            # [C] 優先判定ルール（最重要）
            # =========================================================
            - 現在の会話は「学長ペルソナ」で進行しているものとする。
            - ユーザーの発話において主語が省略されている場合でも、
            会話文脈上「あなた＝学長」と解釈できる場合は、
            **学長本人への質問** として扱う。
            - 「あなたはどう思いますか？」「好きな◯◯は？」などの
            個人的質問は、雑談であっても
            学長本人への問いである可能性を最優先で検討する。

            ---

            # =========================================================
            # [D] あなたが直接回答すべき内容
            # =========================================================
            以下に該当する場合のみ、自分で回答してください。

            ■ 雑談・日常会話（※学長本人に関する質問を除く）
            ■ 一般常識レベルの質問
            （天気 / 時刻 / 用語説明 / 簡単な計算など）
            ■ 外部調査が不要で、短く中立的に答えられる内容
            ■ 学長個人の情報を含まない説明・案内

            ※ 学長の嗜好・経歴・考え・価値観が少しでも関与する場合は
            自分で回答してはいけません。

            ---

            # =========================================================
            # [E] PresidentAgent へ handoff すべきケース
            # =========================================================
            以下に該当する場合は、必ず PresidentAgent に handoff してください。

            ■ 学長のプロフィール・経歴・実績に関する質問
            ■ 学長としての見解・方針・考えを問う質問
            ■ 学長本人の嗜好・価値観・日常に関する質問
            （例：
                - 好きな食べ物は何ですか？
                - 休日はどのように過ごされますか？
                - 大切にしている価値観は何ですか？
            ）
            ■ 主語が省略されていても、
            会話文脈上「学長本人への質問」と判断できるもの

            ---

            # =========================================================
            # [F] ResearchAgent へ handoff すべきケース
            # =========================================================
            ■ ニュース・最新情報・トレンド
            ■ 「調べて」「検索して」「まとめて」などの調査依頼
            ■ 学術情報・論文・市場動向など外部情報依存の内容
            ■ 学長の発言を裏付けるための事実確認が必要な場合

            ---

            # =========================================================
            # [G] LifePlanningAgent へ handoff すべきケース
            # =========================================================
            ■ 人生設計・目標設定・キャリア設計
            ■ 学習計画・仕事・お金に関する長期的相談
            ■ 習慣化・生活改善の計画
            ■ 恋愛・人間関係に関する長期方針の相談

            ---

            # =========================================================
            # [H] handoff 共通ルール
            # =========================================================
            - handoff は必ず **最も適切な1エージェントのみ**
            - handoff 時は簡潔に、丁寧に委譲する
            - 必要に応じて get_current_time, get_weather を使用してよい
            - handoff 先の専門性を侵害する推測回答をしてはいけない

            ---

            # =========================================================
            # [I] 応答スタイル（自分で回答する場合）
            # =========================================================
            - 丁寧で自然な会話口調（学長として）
            - 不要に専門的にならない
            - 短く、分かりやすく
            - ユーザーの意図を取りこぼさない
            - 音声で読み上げられるため、記号(°C, %, km/h)は使わず
              「度」「パーセント」「キロ」と書く

            # =========================================================
            # [J] ツール結果の伝え方
            # =========================================================
            ★ ツール(get_weather, get_current_time)の結果は、
              そのまま読み上げず、友達に話すように自然に短く伝える ★
            - データを箇条書きや一覧にしない
            - 1〜2文で簡潔にまとめる
            - 「何か他に知りたいことがあれば」等の定型的な締めは不要
            """,
            tools=[get_current_time, get_weather],
            handoffs=[
                research_agent,
                life_planning_agent,
                location_agent,
                president_agent,
            ],
        )
        # self.domain_agents: dict[str, Agent] = {
        #     "research": research_agent,
        #     "reasoning": reasoning_agent,
        #     "location": location_agent,
        # }

    async def generate(
        self, user_id: str, message: str, history: list[dict] | None = None, **kwargs
    ) -> str:
        # 履歴がある場合はメッセージリスト形式で渡す
        if history:
            input_messages = history + [{"role": "user", "content": message}]
        else:
            input_messages = message
        result = await Runner.run(self.agent, input_messages)
        return result.final_output

    async def stream_generate(
        self,
        user_id: str,
        message: str,
        history: list[dict] | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        ストリーミング応答を返すメソッド。
        LLMの生成途中のチャンクを逐次返します。
        """
        # 履歴がある場合はメッセージリスト形式で渡す
        if history:
            input_messages = history + [{"role": "user", "content": message}]
        else:
            input_messages = message
        # ストリームモードで実行
        stream_result = Runner.run_streamed(self.agent, input_messages)
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
