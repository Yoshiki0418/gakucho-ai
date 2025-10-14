import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/ws", tags=["Audio Stream"])


@router.websocket("/audio-stream")
async def audio_stream(ws: WebSocket):
    """
    🎙️ 音声入力用WebSocketルート（基盤実装）
    - クライアントからの接続を受け付け
    - 音声データ（バイナリ）や制御メッセージ（JSON）を受信
    - ダミー応答を送信
    """
    await ws.accept()
    print("✅ WebSocket connected: /ws/audio-stream")

    try:
        while True:
            data = await ws.receive()
            if "bytes" in data:
                # 音声データを受信（例：PCM16）
                print(f"🎧 Received audio chunk ({len(data['bytes'])} bytes)")
            elif "text" in data:
                # テキストデータ（制御信号やJSONメッセージ）
                print(f"💬 Received text: {data['text']}")

            # ダミー応答を送信
            await asyncio.sleep(0.5)
            await ws.send_json(
                {
                    "type": "status",
                    "message": "音声を受信しました。現在はダミー応答です。",
                }
            )

    except WebSocketDisconnect:
        print("❌ WebSocket disconnected")

    except Exception as e:
        print(f"⚠️ WebSocket error: {e}")

    finally:
        await ws.close()
        print("🔚 Connection closed.")
