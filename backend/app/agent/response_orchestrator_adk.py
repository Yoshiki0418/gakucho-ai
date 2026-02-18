# Google ADK を使って オーケストレーションを行う例
from app.agent.general_conversation.agent import GeneralConversationAgent
from app.agent.general_conversation.domains import (
    LifePlanningAgent,
    LocationAgent,
    ResearchAgent,
)

# ストリーミング版ラッパーを import
from app.agent.openai_agent import OpenAIGeneralConversationStreamingADKAgent
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# --- OpenAI Agent SDK 側エージェントを組み立てる ---
research_agent = ResearchAgent()
life_planning_agent = LifePlanningAgent()
location_agent = LocationAgent()

gc_agent = GeneralConversationAgent(
    research_agent=research_agent,
    life_planning_agent=life_planning_agent,
    location_agent=location_agent,
)

# --- ADK ラッパー（ストリーミング版） ---
openai_streaming_agent = OpenAIGeneralConversationStreamingADKAgent(
    general_conv_agent=gc_agent,
    name="openai_general_streaming",
    output_key="general_conv_result",
)

# --- 要約エージェント（Sequential の 2段目で使う） ---
summary_agent = LlmAgent(
    name="summary_agent",
    model=LiteLlm(model="openai/gpt-4o-mini"),
    instruction="""
以下は OpenAI の一般対話エージェントの出力です。
これを 2〜3 文に要約してください。

{general_conv_result}
""".strip(),
)

# --- フィラーエージェント（Parallel の中で「つなぎ」担当） ---
filler_agent = LlmAgent(
    name="filler_agent",
    model=LiteLlm(model="openai/gpt-4o-mini"),
    instruction="""
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

# --- 1段目: ParallelAgent（OpenAIストリーミング + フィラー） ---
parallel_agent = ParallelAgent(
    name="general_parallel",
    sub_agents=[
        openai_streaming_agent,  # ストリーミングで本回答
        filler_agent,  # 1ショットでフィラー
    ],
)

# --- 2段目: SequentialAgent で「並列 → 要約」をつなぐ ---
root_agent = SequentialAgent(
    name="general_pipeline",
    sub_agents=[
        parallel_agent,  # ここで general_conv_result が state に書かれる
        summary_agent,  # ここで {general_conv_result} が参照できる
    ],
)

# --- Runner で実行 ---
session_service = InMemorySessionService()
runner = Runner(session_service=session_service, agent=root_agent, app_name="my_app")


async def run_example():
    session = await session_service.create_session(
        app_name="my_app",
        user_id="user1",
    )

    user_content = types.Content(
        role="user",
        parts=[types.Part(text="今何時ですか？")],
    )

    async for event in runner.run_async(
        user_id="user1",
        session_id=session.id,
        new_message=user_content,
    ):
        if not event.content or not event.content.parts:
            continue

        text = event.content.parts[0].text or ""

        # ストリーミングの様子を全部確認したいので、
        # partial / final や author ごとにログを分けてみる
        if event.partial:
            print(f"[PARTIAL][{event.author}]: {text}")
        elif event.is_final_response():
            print(f"[FINAL][{event.author}]: {text}")
        else:
            print(f"[INTERMEDIATE][{event.author}]: {text}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_example())
