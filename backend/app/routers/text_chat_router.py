import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/text-chat", tags=["Text Chat"])


@router.post("/stream")
async def text_chat_stream(request: Request):
    """
    ダミー応答:
    ユーザーの入力を受け取ったら、3回に分けて疑似メッセージをストリーミング返却する。
    """
    body = await request.json()
    user_input = body.get("text", "")

    async def event_stream():
        # 1️⃣ 開始メッセージ
        yield f"data: {json.dumps({'type': 'start', 'message': f'入力を受け取りました: {user_input}'})}\n\n"
        await asyncio.sleep(1)

        # 2️⃣ ダミーの応答を複数回返す
        for i in range(3):
            chunk = f"これはダミー応答の {i+1} 回目です。"
            yield f"data: {json.dumps({'type': 'text_chunk', 'content': chunk})}\n\n"
            await asyncio.sleep(1)

        # 3️⃣ 終了メッセージ
        yield f"data: {json.dumps({'type': 'done', 'message': '完了しました。'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/char-stream")
async def char_stream():
    async def event_stream():
        text = "こんにちは！学長AIです。"
        for ch in text:
            yield f"data: {json.dumps({'type': 'text_chunk', 'content': ch})}\n\n"
            await asyncio.sleep(0.05)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
