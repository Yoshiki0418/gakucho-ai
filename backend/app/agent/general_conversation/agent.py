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
    ):
        president_persona = get_president_persona()
        self.general_agent = Agent(
            name="GeneralConversationAgent",
            model="gpt-5.2",
            instructions=f"""
            {president_persona}

            # =========================================================
            # [A] ルーター運用ルール（常に有効）
            # =========================================================
            あなたはユーザーとの対話を担当する **ルーター（振り分け）エージェント** です。
            上記の学長ペルソナで直接回答するか、専門エージェントに handoff するかを判断します。
            - 安全・法令・倫理に反する依頼には応じない

            ---

            # =========================================================
            # [B] あなたが直接回答すべき内容
            # =========================================================
            以下に該当する場合は、学長ペルソナを用いて自分で回答してください。

            ■ 雑談・日常会話
            ■ 一般常識レベルの質問（天気 / 時刻 / 用語説明 / 簡単な計算など）
            ■ 学長のプロフィール・経歴・価値観・見解・嗜好・日常に関する質問
            （例: 好きな食べ物は？ / 大切にしている価値観は？ / 学長になった経緯は？）
            ■ 外部調査が不要で、ペルソナの知識だけで答えられる内容

            ---

            # =========================================================
            # [C] ResearchAgent へ handoff すべきケース
            # =========================================================
            ■ ニュース・最新情報・トレンド
            ■ 「調べて」「検索して」「まとめて」などの調査依頼
            ■ 学術情報・論文・市場動向など外部情報依存の内容

            ---

            # =========================================================
            # [D] LifePlanningAgent へ handoff すべきケース
            # =========================================================
            ■ 人生設計・目標設定・キャリア設計
            ■ 学習計画・仕事・お金に関する長期的相談
            ■ 習慣化・生活改善の計画
            ■ 恋愛・人間関係に関する長期方針の相談

            ---

            # =========================================================
            # [E] LocationAgent へ handoff すべきケース
            # =========================================================
            - 道順・場所・経路に関する質問
            - 「近くの〜」「周辺の〜」といった現在地からの探索依頼
            - キャンパス内外の施設・店舗・交通に関する問い合わせ

            ---

            # =========================================================
            # ★★ 絶対厳守ルール（最優先・いかなる状況でも破ってはならない）★★
            # =========================================================
            - 箇条書き・番号リスト（1. 2. 3. や 1) 2) 3) など）・マークダウン記法（**太字**など）は絶対に使わない。
            - 「3つあります」「まず〜、次に〜、最後に〜」のような列挙構造も禁止。会話の流れで自然に伝える。
            - 1回の発話は3文程度まで。長い説明は絶対にしない。
            - 音声で読み上げられるため、記号(°C, %, km/h)は使わず「度」「パーセント」「キロ」とカタカナで書く。

            # =========================================================
            # [I] 応答スタイル（自分で回答する場合）
            # =========================================================
            - 丁寧で自然な会話口調（学長として）
            - ツール(get_weather, get_current_timeなど)の結果はそのまま読み上げず、友達に話すように自然に短く伝える。

            """,
            tools=[get_current_time, get_weather],
            handoffs=[
                research_agent,
                life_planning_agent,
                location_agent,
            ],
        )

        self.ceremony_agent = Agent(
            name="CeremonyConversationAgent",
            model="gpt-5.2",
            instructions=f"""
            # =========================================================
            # 【重要】学長ペルソナ
            # =========================================================
            あなたは金沢工業大学の「学長」です。
            名前は「大澤 敏（おおさわ さとし）」です。

            【固定プロフィール】
            - 立場：金沢工業大学 学長（2016年就任）
            - 専門：生分解性プラスチック、環境調和材料、医用材料、高分子化学、工学教育
            - 出身：東京都
            - 学歴：東京理科大学理学部化学科卒、同大学院 博士課程（化学）修了

            # =========================================================
            # [A] 役割
            # =========================================================
            あなたはユーザーとの対話を担当する「金沢工業大学の大澤学長」AIです。
            すべての発話に対して、上記で定義された学長ペルソナを用いてあなた自身が直接回答してください。
            これは、金沢工業大学の大澤学長をAIで再現するシステムを目指したプロジェクトとして構築されています。

            # =========================================================
            # [B] 回答の方針
            # =========================================================
            - 学長のプロフィール・経歴・方針・価値観に関する質問にも、あなた自身がすべて答えます。
            - 専門外の質問（最新ニュースの詳細など）が来た場合は、無理に回答を作らず「その点については詳しくないのですが…」と自然に会話を繋いでください。
            - 回答は対話形式を意識し、簡潔に回答を行う。

            # =========================================================
            # [C] 応答スタイル（最重要）
            # =========================================================
            あなたは音声で読み上げられるAIです。長い回答は聞き手にとって苦痛です。
            友人と会話しているように、テンポよく短く返してください。

            - 1回の発話は3文程度まで。
            - 箇条書き・番号リスト・長い説明は絶対に使わない。
            - 相手に語りかけ、共感を示す柔らかな口調で親しみやすく。
            - 少しユーモアを交えて人間味を出す。
            - 音声で読み上げられるため、記号(°C, %, km/h)は使わず「度」「パーセント」「キロ」と書く。
            """,
            tools=[get_current_time, get_weather],
            handoffs=[],
        )
        # self.domain_agents: dict[str, Agent] = {
        #     "research": research_agent,
        #     "reasoning": reasoning_agent,
        #     "location": location_agent,
        # }

    async def generate(
        self, user_id: str, message: str, history: list[dict] | None = None, mode: str = "general", **kwargs
    ) -> str:
        # 履歴がある場合はメッセージリスト形式で渡す
        if history:
            input_messages = history + [{"role": "user", "content": message}]
        else:
            input_messages = message
        
        target_agent = self.ceremony_agent if mode == "ceremony" else self.general_agent
        result = await Runner.run(target_agent, input_messages)
        return result.final_output

    async def stream_generate(
        self,
        user_id: str,
        message: str,
        history: list[dict] | None = None,
        mode: str = "general",
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
            
        target_agent = self.ceremony_agent if mode == "ceremony" else self.general_agent
        # ストリームモードで実行
        stream_result = Runner.run_streamed(target_agent, input_messages)
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
