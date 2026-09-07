import os
import time
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

# ★実験条件: endogenous フィラー指示ブロック（FILLER_MODE=endogenous のときのみ挿入）
# 本物の内因的フィラー：フィラーの内容は**モデル自身が文脈から生成**する。
# コード側でのテンプレ注入（フォールバック）は行わない。
ENDOGENOUS_FILLER_INSTRUCTION = """
# =========================================================
# [L] フィラー（つなぎ言葉）— 自己判断で出す ★実験条件: endogenous★
# =========================================================
ツール呼び出しや内部処理には待ち時間が発生します。
その「間（ま）」を、**学長として自然な一言**で埋めてください。

【最重要・例外なし】
- ツールを呼ぶ直前、または別エージェントに処理を委ねる直前に、
  必ずつなぎの1文をテキストで出力してから関数を呼び出すこと。
  「無言でツール/handoff を実行する」ことは固く禁止する。

【つなぎの一言の作り方】
- ユーザーの発話に軽く触れた、自然な口語の1文。毎回表現を変える。
  ✅ 良い例：「天気ですね、ちょっと確認しますね。」
  ✅ 良い例：「なるほど、少し調べてみますね。」
  ✅ 良い例：「それは私もしっかり確認してみます。」
  ✅ 良い例：「場所の情報は、少し見てみますね。」
- 結論・事実・数値はこの一言に含めない（「受け止め」と「予告」だけ）。
- 「少々お待ちください」のような機械的な定型文は使わない。

【絶対禁止ワード】
- 「引き継ぎ」「担当」「専門エージェント」「委譲」「transfer」「handoff」
  → 内部システムの仕組みを口に出してはいけない。
  → 学長として自分が調べる・確認するように自然に話すこと。

【フィラーが不要なケース】
- ツールも別エージェントも使わず、その場で即答できる短い雑談・挨拶。
"""


CEREMONY_ENDOGENOUS_FILLER_INSTRUCTION = """
# =========================================================
# [X] フィラー（つなぎ言葉）— 自己判断で出す ★実験条件: endogenous★
# =========================================================
- ツールを呼ぶ直前に、まず内容に触れた自然なつなぎの1文を出力してからツールを実行すること。
  ✅ 良い例：「天気ですね、ちょっと確認しますね。」
  ✅ 良い例：「いまの時間を確認してみますね。」
- 結論や数値はこの一言に含めない。機械的な定型文（「少々お待ちください」等）は禁止。
- 「引き継ぎ」「担当」など内部システムを示す言葉は使わない。
- ツールを使わず即答できる場合はフィラー不要。
"""

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
        endogenous_filler: bool = False,
    ):
        president_persona = get_president_persona()
        # メイン会話のデフォルトモデル。リクエストでモデル指定が無い場合はこれを使う。
        self.DEFAULT_MODEL = "gpt-5.2"
        # motion と同型：endogenous モードでは、フィラー生成プロンプトをエージェント指示に
        # 挿入するだけ。フィラーの内容はメインエージェント自身が文脈から生成する。
        # （reasoning 設定やテンプレ・フォールバックなどの追加機構は使わない）
        _filler_block = ENDOGENOUS_FILLER_INSTRUCTION if endogenous_filler else ""
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
            - 天気・場所・道順などで都市や場所が明示されていない場合は、絶対に「どの都市ですか？」等と聞き返さない。
              あなたの現在地は金沢工業大学（石川県・金沢）である。都市未指定の天気は現在地「金沢」を既定として、
              そのまま get_weather を呼び出して答えること。

            # =========================================================
            # [I] 応答スタイル（自分で回答する場合）
            # =========================================================
            - 丁寧で自然な会話口調（学長として）
            - ツール(get_weather, get_current_timeなど)の結果はそのまま読み上げず、友達に話すように自然に短く伝える。

            {_filler_block}
            """,
            tools=[get_current_time, get_weather],
            handoffs=[
                research_agent,
                life_planning_agent,
                location_agent,
            ],
        )

        # endogenous モード用：同じ構成にフィラー指示を追記したエージェントを常時保持
        self.general_agent_endogenous = Agent(
            name="GeneralConversationAgent",
            model="gpt-5.2",
            instructions=self.general_agent.instructions + "\n" + ENDOGENOUS_FILLER_INSTRUCTION,
            tools=[get_current_time, get_weather],
            handoffs=[
                research_agent,
                life_planning_agent,
                location_agent,
            ],
        )

        _ceremony_filler_block = ""  # endogenous 版は ceremony_agent_endogenous で処理
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
            - 天気で都市が明示されていない場合は「どの都市ですか？」等と聞き返さず、現在地である金沢工業大学（金沢）の天気を答えること。

            {_ceremony_filler_block}
            """,
            tools=[get_current_time, get_weather],
            handoffs=[],
        )

        self.ceremony_agent_endogenous = Agent(
            name="CeremonyConversationAgent",
            model="gpt-5.2",
            instructions=self.ceremony_agent.instructions + "\n" + CEREMONY_ENDOGENOUS_FILLER_INSTRUCTION,
            tools=[get_current_time, get_weather],
            handoffs=[],
        )

        # self.domain_agents: dict[str, Agent] = {
        #     "research": research_agent,
        #     "reasoning": reasoning_agent,
        #     "location": location_agent,
        # }

    def _resolve_agent(
        self, mode: str, filler_mode: str, llm_model: str | None = None
    ) -> Agent:
        """mode / filler_mode / llm_model から使用する Agent を決定する。

        既定モデル(gpt-5.2)なら事前生成済みの Agent をそのまま使う（従来挙動を維持）。
        別モデルが指定された場合のみ、指示文・ツール・handoff を引き継いだ
        新しい Agent をモデル差し替えで生成する。
        """
        endogenous = filler_mode == "endogenous"
        if mode == "ceremony":
            base = self.ceremony_agent_endogenous if endogenous else self.ceremony_agent
        else:
            base = self.general_agent_endogenous if endogenous else self.general_agent

        model = llm_model or self.DEFAULT_MODEL
        if model == self.DEFAULT_MODEL:
            return base

        return Agent(
            name=base.name,
            model=model,
            instructions=base.instructions,
            tools=base.tools,
            handoffs=base.handoffs,
        )

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
        filler_mode: str = "dynamic",
        timing_data: dict | None = None,
        llm_model: str | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        ストリーミング応答を返すメソッド。
        LLMの生成途中のチャンクを逐次返します。
        llm_model を指定すると、そのモデルでメイン会話エージェントを生成して応答します。
        """
        if history:
            input_messages = history + [{"role": "user", "content": message}]
        else:
            input_messages = message

        target_agent = self._resolve_agent(mode, filler_mode, llm_model)
        stream_result = Runner.run_streamed(target_agent, input_messages)

        # 論文用ログ: ツール/handoff 前テキスト（endogenousフィラー）と TTFT を計測
        t_start = time.perf_counter()
        ttft_ms: float | None = None
        pre_tool_text = ""
        tool_or_handoff_detected = False

        async for event in stream_result.stream_events():
            if not (event.type == "raw_response_event" and hasattr(event.data, "type")):
                continue

            if (
                event.data.type == "response.output_text.delta"
                and hasattr(event.data, "delta")
            ):
                delta = event.data.delta
                if delta:
                    if ttft_ms is None:
                        ttft_ms = (time.perf_counter() - t_start) * 1000
                    if not tool_or_handoff_detected:
                        pre_tool_text += delta
                    yield delta

            elif (
                event.data.type == "response.output_item.added"
                and hasattr(event.data, "item")
                and getattr(event.data.item, "type", None) == "function_call"
                and not tool_or_handoff_detected
            ):
                # モデルがツール/handoff を呼んだ時点を記録するだけ。
                # 本物の内因的フィラーでは、この直前にモデル自身が出したテキスト
                # (pre_tool_text) がフィラーになる。コードによるフォールバック注入はしない。
                tool_or_handoff_detected = True

        ttft_str = f"{ttft_ms:.1f}" if ttft_ms is not None else "N/A"
        # endogenous 条件で「ツール/handoff の前にモデル自身がフィラーを出したか」を正確に記録。
        # （論文用：このフラグの False 率＝モデルのフィラー省略率）
        model_emitted_filler = bool(
            filler_mode == "endogenous"
            and tool_or_handoff_detected
            and pre_tool_text.strip()
        )
        print(
            f"[agent_log] filler_mode={filler_mode} "
            f"ttft_ms={ttft_str} "
            f"tool_called={tool_or_handoff_detected} "
            f"model_emitted_filler={model_emitted_filler} "
            f"pre_tool_text={repr(pre_tool_text.strip())}"
        )
        if timing_data is not None:
            timing_data["model_filler_fired"] = model_emitted_filler
            timing_data["model_filler_text"] = pre_tool_text.strip()
