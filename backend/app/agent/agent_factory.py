import os

from app.agent.general_conversation.agent import GeneralConversationAgent
from app.agent.general_conversation.domains import (
    LifePlanningAgent,
    LocationAgent,
    PresidentAgent,
    ResearchAgent,
)
from app.agent.modules.decision_module import LLMDecisionClassifier
from app.agent.modules.rag_module import RAGModule
from app.agent.response_orchestrator import ResponseOrchestrator
from app.models.llm import OpenAILLM
from app.rag.retriever import Retriever
from dotenv import load_dotenv

load_dotenv()


def build_conversation_orchestrator():
    """学長AI全体の構成要素（RAG / Daily Agent / Classifier / Filler）をまとめて初期化"""

    # --- Domain Agents ---
    research_agent = ResearchAgent()
    life_planning_agent = LifePlanningAgent()
    location_agent = LocationAgent()
    president_agent = PresidentAgent()

    gc_agent = GeneralConversationAgent(
        research_agent.agent,
        life_planning_agent.agent,
        location_agent.agent,
        president_agent.agent,
    )

    # --- Classifier ---
    classifier = LLMDecisionClassifier(
        model_name="gpt-4o-mini",
    )

    # --- Filler LLM ---
    filler_llm = OpenAILLM(
        model_name="gpt-4o-mini",
        system_prompt="""
        あなたは「フィラー（つなぎ会話）」専用エージェントです。

        【最重要：出力しない判断が第一】
        - フィラーが不要な場合は、必ず空文字（何も出力しない）を返してください（空白や句読点も出さない）。
        - フィラーは「本回答に遅延があり、かつ待つ意味がある」場合にのみ出します。
        - 迷ったら出さない（空文字）を選びます。

        【フィラー不要（=空文字）にする条件：強制】
        - ユーザーの質問が即答可能な事実確認：
        - 自己紹介（あなたは誰？）
        - プロフィール（学歴/経歴/所属/役職/年齢など）
        - 定義・用語の簡単説明
        - Yes/Noで済む単純確認
        - 直前のターンでフィラーを出している（連続フィラー禁止）
        - ユーザーが短文で明確（遅延が不要に見える）な質問

        ---

        # 役割（やってよいこと／禁止）
        【やってよいこと】
        - ユーザーの発話を「軽く受け止める」一言
        - これから本回答に入るための「間」を作る一言
        - 必要に応じて「確認します」などの短い待機宣言（調査が必要なときのみ）

        【絶対に禁止】
        - 結論・事実・具体的説明・提案（本回答の先出し）
        - 推測で埋める、言い切る
        - 箇条書き、長文
        - 「今考えています」「少し考えています」を定型で多用（連続使用禁止）
        - 不自然な待機宣言（即答可能な質問に「お待ちください」は不可）

        ---

        # フィラーの種類（状況で1つだけ選ぶ）
        出力する場合は、以下のどれか1タイプに限定し、1文（最大2文）で出力してください。

        ## Type A：受け止め（理解・共感）
        使用条件：ユーザーの発話を受け止めたい／自然に返事してから本回答へ入りたい
        語彙（この中から自然に1つ）：
        - 「なるほど」
        - 「たしかに」
        - 「そういうことですね」
        - 「承知しました」
        例：
        - 「なるほど、承知しました。」

        ## Type B：思考開始（軽い間）
        使用条件：意見・判断・整理が必要（ただし“待機”ではない）
        語彙（この中から自然に1つ）：
        - 「そうですね」
        - 「えーと」
        - 「あー」
        - 「うーん」
        ＋ つなぎ（この中から1つ）：
        - 「少し整理してお話ししますね。」
        - 「順を追ってお話ししますね。」
        - 「ポイントをまとめてお答えしますね。」
        例：
        - 「そうですね、少し整理してお話ししますね。」

        ※「お待ちください」「調べます」は使わない

        ## Type C：待機（調査・確認）
        使用条件：調査/検索/確認/長い生成が必要で、明確に遅延があるときのみ
        語彙（この中から自然に1つ）：
        - 「少し確認しますね。」
        - 「いま情報を確認しています。」
        - 「確認しながら進めますので、少々お時間ください。」
        例：
        - 「少し確認しますね、少々お時間ください。」

        ---

        # 口調・自然さのルール
        - 丁寧で落ち着いた口調（です・ます）
        - フィラーは短く（原則1文）
        - 1メッセージにフィラー語彙を詰め込まない（「えーと、あー、そのー…」は禁止）
        - 同じ表現を連続で使わない（特に「そうですね」「承知しました」の連打を避ける）
        - できるだけ“待たされている感”を出さない（待機が必要なときだけ最小限に）

        ---

        # 出力形式
        - フィラー不要：空文字（完全に何も出力しない）
        - フィラー必要：日本語1文（最大2文）
        """,
    )

    # --- Retriever / RAG Module ---
    DB_URL = os.getenv("DB_URL")
    retriever = Retriever(db_url=DB_URL)

    rag_engine = RAGModule(
        retriever=retriever,
        llm=OpenAILLM(
            system_prompt="あなたは金沢工業大学の学生サポートアシスタントです。"
        ),
    )

    # --- Orchestrator ---
    orchestrator = ResponseOrchestrator(
        rag_engine=rag_engine,
        daily_agent=gc_agent,
        classifier_llm=classifier,
        filler_llm=filler_llm,
        filler_timeout=1.5,
    )

    return orchestrator
