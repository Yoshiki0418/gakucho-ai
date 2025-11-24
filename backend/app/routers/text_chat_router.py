import asyncio
import json

from app.agent.general_conversation.agent import GeneralConversationAgent
from app.agent.general_conversation.domains import ResearchAgent
from app.models import llm, tts
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/text-chat", tags=["Text Chat"])


@router.get("/stream")
async def text_chat_stream(request: Request):
    user_input = request.query_params.get("text", "こんにちは！")
    history = request.query_params.get("history", [])

    # モデル選択（オプション）
    llm_provider = request.query_params.get("llm_provider", None)
    llm_model = request.query_params.get("llm_model", None)
    tts_provider = request.query_params.get("tts_provider", None)
    tts_voice = request.query_params.get("tts_voice", None)

    if llm_model or tts_voice:
        from app.models.model_registry import create_llm, create_tts

        system_prompt = (
            "あなたは金沢工業大学の学長です。親しみやすく、丁寧に回答してください。"
        )

        _llm = create_llm(
            llm_provider or "openai",
            llm_model or "gpt-4o-mini",
            system_prompt=system_prompt,
        )
        _tts = create_tts(tts_provider or "style-bert-vits2")
    else:
        _llm, _tts = llm, tts

    async def event_stream():
        yield f"data: {json.dumps({'type': 'start', 'message': f'{_llm.model_name} を使用します'})}\n\n"

        text_output = await _llm.generate(user_input, history)

        # TTSを並行で実行
        tts_task = asyncio.create_task(
            asyncio.to_thread(_tts.synthesize_to_base64, text_output)
        )
        yield f"data: {json.dumps({'type': 'text_result', 'content': text_output})}\n\n"

        audio_b64 = await tts_task
        yield f"data: {json.dumps({'type': 'audio_result', 'audio': audio_b64})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'message': '応答完了'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/char-stream")
async def char_stream(request: Request):
    user_input = request.query_params.get("text", "こんにちは！")
    history = request.query_params.get("history", [])

    # モデル選択（オプション）
    llm_provider = request.query_params.get("llm_provider", None)
    llm_model = request.query_params.get("llm_model", None)
    tts_provider = request.query_params.get("tts_provider", None)
    tts_voice = request.query_params.get("tts_voice", None)

    if llm_model or tts_voice:
        from app.models.model_registry import create_llm, create_tts

        system_prompt = (
            "あなたは金沢工業大学の学長です。"
            "常に相手の意図を正確に理解し、思いやりのある自然な言葉で説明します。"
            "ユーザーを生徒として話し、長すぎる説明は避け、テンポよく短めの発言を心がけてください。"
        )

        _llm = create_llm(
            llm_provider or "openai",
            llm_model or "gpt-4o-mini",
            system_prompt=system_prompt,
        )
        _tts = create_tts(tts_provider or "style-bert-vits2")
    else:
        _llm, _tts = llm, tts

    PUNCTUATIONS = {"。", "！", "？", "!", "?"}

    async def event_stream():
        yield f"data: {json.dumps({'type': 'start', 'message': f'{_llm.model_name} を使用します'})}\n\n"

        sentence_buffer = ""

        # LLMのストリーミング出力を逐次処理
        async for chunk in _llm.stream_generate(user_input, history):
            text_piece = str(chunk)
            sentence_buffer += text_piece

            yield f"data: {json.dumps({'type': 'text_chunk', 'content': text_piece})}\n\n"

            # 文の終端を検出したら、その文をTTSに渡す
            if any(p in text_piece for p in PUNCTUATIONS):
                # 並列で音声生成
                current_sentence = sentence_buffer.strip()
                audio_b64 = await asyncio.to_thread(
                    _tts.synthesize_to_base64, current_sentence
                )

                yield f"data: {json.dumps({'type': 'audio_chunk', 'sentence': current_sentence, 'audio': audio_b64})}\n\n"

                # 文バッファをリセット
                sentence_buffer = ""

        # 最後に残った文を処理（句読点なしで終わった場合）
        if sentence_buffer.strip():
            audio_b64 = await asyncio.to_thread(
                _tts.synthesize_to_base64, sentence_buffer.strip()
            )
            yield f"data: {json.dumps({'type': 'audio_chunk', 'sentence': sentence_buffer.strip(), 'audio': audio_b64})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'message': '応答完了'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/char-stream-agent")
async def char_stream_agent(request: Request):
    user_input = request.query_params.get("text", "こんにちは！")
    # history = request.query_params.get("history", [])

    # モデル選択（オプション）
    tts_provider = request.query_params.get("tts_provider", None)
    tts_voice = request.query_params.get("tts_voice", None)
    research_agent = ResearchAgent()
    agent = GeneralConversationAgent(research_agent.agent)

    if tts_voice:
        from app.models.model_registry import create_tts

        _tts = create_tts(tts_provider or "style-bert-vits2")
    else:
        _tts = tts

    PUNCTUATIONS = {"。", "！", "？", "!", "?"}

    async def event_stream():
        sentence_buffer = ""

        # LLMのストリーミング出力を逐次処理
        async for chunk in agent.stream_generate(user_id="1", message=user_input):
            text_piece = str(chunk)
            sentence_buffer += text_piece

            yield f"data: {json.dumps({'type': 'text_chunk', 'content': text_piece})}\n\n"

            # 文の終端を検出したら、その文をTTSに渡す
            if any(p in text_piece for p in PUNCTUATIONS):
                # 並列で音声生成
                current_sentence = sentence_buffer.strip()
                audio_b64 = await asyncio.to_thread(
                    _tts.synthesize_to_base64, current_sentence
                )

                yield f"data: {json.dumps({'type': 'audio_chunk', 'sentence': current_sentence, 'audio': audio_b64})}\n\n"

                # 文バッファをリセット
                sentence_buffer = ""

        # 最後に残った文を処理（句読点なしで終わった場合）
        if sentence_buffer.strip():
            audio_b64 = await asyncio.to_thread(
                _tts.synthesize_to_base64, sentence_buffer.strip()
            )
            yield f"data: {json.dumps({'type': 'audio_chunk', 'sentence': sentence_buffer.strip(), 'audio': audio_b64})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'message': '応答完了'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
