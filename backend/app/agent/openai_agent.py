# Google ADKで使用するためのラップクラス
from typing import AsyncGenerator

from app.agent.general_conversation.agent import GeneralConversationAgent
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types
from typing_extensions import override


class OpenAIGeneralConversationStreamingADKAgent(BaseAgent):
    """
    OpenAI Agent SDK の GeneralConversationAgent を
    「ストリーミングで」ラップする ADK エージェント。

    - OpenAI 側の stream_generate() から delta を受け取る
    - delta ごとに Event(partial=True) を yield
    - 最後に全文 + state_delta[output_key] を持つ Event(partial=False) を 1 回 yield
    """

    general_conv_agent: GeneralConversationAgent
    output_key: str = "general_conversation_result"

    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        general_conv_agent: GeneralConversationAgent,
        name: str = "openai_general_conversation_streaming",
        description: str | None = None,
        output_key: str = "general_conversation_result",
    ) -> None:
        if description is None:
            description = (
                "OpenAI Agent SDK の GeneralConversationAgent を "
                "ストリーミング実行する ADK エージェント"
            )

        super().__init__(
            name=name,
            description=description,
            sub_agents=[],
            general_conv_agent=general_conv_agent,
            output_key=output_key,
        )

    @override
    async def _run_async_impl(
        self,
        ctx: InvocationContext,
    ) -> AsyncGenerator[Event, None]:
        """
        - ctx.user_content からテキストを抽出
        - general_conv_agent.stream_generate(...) を呼び出し
        - delta ごとに partial=True の Event をストリーム出力
        - 生成終了後、全文 + state_delta を持つ final Event を 1 つ返す
        """
        # 1. user_content → プレーンテキスト
        user_text = ""
        if ctx.user_content and ctx.user_content.parts:
            texts: list[str] = []
            for part in ctx.user_content.parts:
                text = getattr(part, "text", None)
                if text:
                    texts.append(text.strip())
            user_text = " ".join(texts)

        if not user_text:
            msg = "ユーザー入力が取得できなかったため、OpenAIストリーミングエージェントを実行できませんでした。"
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=msg)],
                ),
                actions=EventActions(
                    state_delta={self.output_key: msg},
                ),
            )
            return

        user_id = ctx.user_id or "adk_user"

        buffer = ""

        try:
            async for delta in self.general_conv_agent.stream_generate(
                user_id=user_id,
                message=user_text,
            ):
                if not delta:
                    continue

                buffer += delta

                yield Event(
                    author=self.name,
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text=delta)],
                    ),
                    # ADK 的には partial=True が「ストリーミング中のテキストチャンク」のサインになる
                    partial=True,
                )
        except Exception as e:
            err_msg = (
                f"OpenAIエージェントのストリーミング実行中にエラーが発生しました: {e}"
            )
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=err_msg)],
                ),
                actions=EventActions(
                    state_delta={self.output_key: err_msg},
                ),
            )
            return

        if buffer:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=buffer)],
                ),
                partial=False,
                actions=EventActions(
                    state_delta={self.output_key: buffer},
                ),
            )
        else:
            msg = "OpenAIエージェントから有効なテキストが生成されませんでした。"
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=msg)],
                ),
                actions=EventActions(
                    state_delta={self.output_key: msg},
                ),
            )
