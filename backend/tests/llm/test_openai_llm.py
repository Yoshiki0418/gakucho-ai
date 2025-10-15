import pytest
import tiktoken
from app.models.llm.openai_llm import OpenAILLM


# ───────────────────────────────
# 非ストリーミング生成のテスト
# ───────────────────────────────
@pytest.mark.asyncio
async def test_generate_response_with_token_count(monkeypatch):
    model_name = "gpt-4o"
    llm = OpenAILLM(model_name=model_name)

    message_text = "これはテスト用の文章です。"

    encoding = tiktoken.encoding_for_model(model_name)
    expected_prompt_tokens = len(encoding.encode(message_text))

    async def mock_generate_impl(*args, **kwargs):
        return "これはモックされた応答です。"

    monkeypatch.setattr(llm, "_generate_impl", mock_generate_impl)

    result = await llm.generate(
        message=message_text,
        history=[],
        token_count=True,
    )
    expected_completion_tokens = len(encoding.encode("これはモックされた応答です。"))

    assert result.prompt_tokens == expected_prompt_tokens
    assert result.completion_tokens == expected_completion_tokens


# ───────────────────────────────
# ストリーミング生成のテスト
# ───────────────────────────────
@pytest.mark.asyncio
async def test_stream_generate(monkeypatch):
    llm = OpenAILLM(model_name="gpt-4o-mini")

    history = [
        {"role": "assistant", "content": "こんにちは、何かお困りですか？"},
    ]

    # ストリーム出力をモック
    async def mock_stream_generate(*args, **kwargs):
        for token in ["テ", "ス", "ト"]:
            yield token

    monkeypatch.setattr(llm, "stream_generate", mock_stream_generate)

    tokens = []
    async for chunk in llm.stream_generate(
        message="ストリームテスト",
        history=history,
    ):
        tokens.append(chunk)

    assert "".join(tokens) == "テスト"
