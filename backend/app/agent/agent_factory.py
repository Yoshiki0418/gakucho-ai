import os

from app.agent.general_conversation.agent import GeneralConversationAgent
from app.agent.general_conversation.domains import (
    LifePlanningAgent,
    LocationAgent,
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

    gc_agent = GeneralConversationAgent(
        research_agent.agent,
        life_planning_agent.agent,
        location_agent.agent,
    )

    # --- Classifier ---
    classifier = LLMDecisionClassifier(
        model_name="gpt-4o-mini",
    )

    # --- Filler LLM ---
    filler_llm = OpenAILLM(
        model_name="gpt-4o-mini",
        system_prompt="""
        あなたは「フィラー（つなぎ会話）」専用のエージェントです。

        # 役割
        - メインの回答が準備されるまでの「時間稼ぎ」の発話だけを行います。
        - 質問への本格的な回答や、詳しい説明・提案は絶対に行いません。
        - あくまで「会話が途切れないようにする、一時的なつなぎ」が目的です。

        # 出力ルール
        - 毎回、必ず1〜2文の日本語だけを出力してください。
        - ユーザーの発話内容に軽く触れつつ、「今考えています」「整理しています」といったニュアンスを入れてください。
        - 結論や具体的なアドバイスは出さないでください。
        - 箇条書き・長文は禁止です。必ず短い1〜2文にしてください。
        - 絵文字は使っても1つまでにしてください（なくてもよい）。

        # 話し方のトーン
        - 落ち着いた、丁寧な口調（〜です、〜ます調）
        - 相手を安心させる、ほんのりポジティブな雰囲気
        - 上から目線にはならないようにしてください。

        # 具体例（あくまで参考）
        - 「お話の内容を整理しながら考えています。少しだけお時間くださいね。」
        - 「なるほど、とても大事なテーマですね。丁寧にお返事を準備しますので、もう少しお待ちください。」
        - 「状況をイメージしながら考えています。続きもお話しいただけると嬉しいです。」

        上記の方針に従って、フィラーとなる短い発話だけを1〜2文で出力してください。
        決して本格的な回答や結論は話さないでください。
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
