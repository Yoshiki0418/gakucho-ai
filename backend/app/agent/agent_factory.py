import os

from app.agent.general_conversation.agent import GeneralConversationAgent
from app.agent.general_conversation.domains import (
    EventGreetingAgent,
    LifePlanningAgent,
    LocationAgent,
    PresidentAgent,
    ResearchAgent,
)
from app.agent.modules.decision_module import LLMDecisionClassifier
from app.agent.modules.rag_module import RAGModule
from app.agent.response_orchestrator import ResponseOrchestrator
from app.models.llm import GemmaLLM, OpenAILLM
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
    event_greeting_agent = EventGreetingAgent()

    gc_agent = GeneralConversationAgent(
        research_agent.agent,
        life_planning_agent.agent,
        location_agent.agent,
        president_agent.agent,
        event_greeting_agent.agent,
    )

    # --- Classifier (ローカル Gemma で高速分類) ---
    classifier_llm = GemmaLLM(
        model_name="google/gemma-2-2b-jpn-it",
        system_prompt="あなたは分類器です。ユーザー発話を候補ラベルから1つ選び、JSONのみ返してください。",
    )
    classifier = LLMDecisionClassifier(
        llm=classifier_llm,
    )

    # --- Filler LLM ---
    filler_llm = OpenAILLM(
        model_name="gpt-4o-mini",
        system_prompt="""あなたはフィラー（つなぎ会話）専用です。
ユーザーの発話内容をふまえ、自然な一言を1文だけ返してください。

■ 不要なら空文字を返す（即答可能な質問/自己紹介/Yes-No/短文は空文字）
■ 禁止: 結論・事実・提案・箇条書き・長文・「お待ちください」
■ 丁寧語（です・ます）。毎回違う表現を使い、同じフレーズを繰り返さない。

■ フィラーの方向性（1つ選択、具体的な言い回しは自由に考えること）
A) 受け止め — ユーザーの発話内容に触れて軽く共感や理解を示す
B) 思考の予告 — これから考えて答える旨を、発話内容に絡めて自然に伝える
C) 確認の予告 — 調査や検索が必要なとき、何を確認するか具体的に一言添える

■ 重要: 上記は方向性の指針であり、定型文ではない。
  ユーザーが何について話しているかを反映した、その場限りの自然な一言を生成すること。

■ 出力: 不要→空文字 / 必要→日本語1文のみ""",
    )

    # --- Retriever / RAG Module ---
    DB_URL = os.getenv("DB_URL")
    retriever = Retriever(db_url=DB_URL)

    rag_engine = RAGModule(
        retriever=retriever,
        llm=GemmaLLM(
            model_name="google/gemma-2-2b-jpn-it",
            system_prompt="あなたは金沢工業大学の学生サポートアシスタントです。"
        ),
    )

    # --- Orchestrator ---
    orchestrator = ResponseOrchestrator(
        rag_engine=rag_engine,
        daily_agent=gc_agent,
        classifier_llm=classifier,
        filler_llm=filler_llm,
        filler_timeout=0.5,
    )

    return orchestrator
