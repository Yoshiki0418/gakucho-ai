import asyncio
import base64
import io
import json
import queue as sync_queue  # ← AvatarStreamer 内部の Queue と区別するため
from typing import Dict

import cv2
import numpy as np
import soundfile as sf
from app.agent.general_conversation.agent import GeneralConversationAgent
from app.agent.general_conversation.domains import (
    LifePlanningAgent,
    LocationAgent,
    ResearchAgent,
)
from app.models import llm, tts
from app.models.lipsync.ditto_batch_streamer import AvatarStreamer
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
    life_planning_agent = LifePlanningAgent()
    location_agent = LocationAgent()
    agent = GeneralConversationAgent(
        research_agent.agent, life_planning_agent.agent, location_agent.agent
    )

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


CFG_PKL = "/workspace/backend/app/weights/lipsync/ditto_cfg/v0.4_hubert_cfg_pytorch.pkl"
DATA_ROOT = "/workspace/backend/app/weights/lipsync/ditto_pytorch"
SOURCE_IMAGE = "test.jpg"


def audio_b64_to_array(audio_b64: str, target_sr: int = 16000) -> np.ndarray:
    audio_bytes = base64.b64decode(audio_b64)
    # soundfile でメモリ上から読む
    data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
    if data.ndim == 2:
        data = data.mean(axis=1)  # stereo → mono
    if sr != target_sr:
        import librosa

        data = librosa.resample(data, orig_sr=sr, target_sr=target_sr)
        sr = target_sr
    return data


def sse_event(event_type: str, payload: dict) -> str:
    data = {"type": event_type, **payload}
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def push_audio_and_stream_frames(
    audio_b64: str,
    avatar_streamer: AvatarStreamer,
    out_queue: "asyncio.Queue[str]",
    frame_index_state: Dict[str, int],
    fps: int = 24,
):
    """
    1文ぶんの音声を Ditto に push し、
    その時点までに生成されたフレームを frame_chunk として SSEキューに積む。
    """

    # 1) 音声を Ditto に投入
    def _push():
        arr = audio_b64_to_array(audio_b64, target_sr=16000)
        avatar_streamer.push_audio_array(arr, sr=16000)

    await asyncio.to_thread(_push)

    # 2) 今キューに溜まっているフレームだけ non-blocking で回収
    frames = []
    while True:
        try:
            frame = avatar_streamer.frame_output_queue.get_nowait()
        except sync_queue.Empty:
            break

        if frame is None:
            # 終了シグナル
            break

        frames.append(frame)

    # 3) SSE キューに frame_chunk を積む
    for frame in frames:
        frame_bgr = frame[:, :, ::-1]
        ok, buf = cv2.imencode(".jpg", frame_bgr)
        if not ok:
            continue
        img_b64 = base64.b64encode(buf).decode("ascii")

        idx = frame_index_state["value"]
        frame_index_state["value"] += 1

        await out_queue.put(
            sse_event(
                "frame_chunk",
                {
                    "frame_index": idx,
                    "fps": fps,
                    "image": img_b64,
                },
            )
        )


# --- Ditto / AvatarStreamer のセットアップ ---
avatar_streamer = AvatarStreamer(
    CFG_PKL,
    DATA_ROOT,
    online_mode=False,  # 先頭フレーム欠損を避けるため False 推奨
    output_path="dummy.mp4",  # 使わないが必須なら適当でOK
)
avatar_streamer.setup(
    SOURCE_IMAGE,
    "./dummy_output.mp4",
    online_mode=False,
)


@router.get("/char-stream-agent-avatar")
async def char_stream_agent_avatar(request: Request):
    user_input = request.query_params.get("text", "こんにちは！")

    # --- Agent / TTS の準備 ---
    tts_provider = request.query_params.get("tts_provider", None)
    tts_voice = request.query_params.get("tts_voice", None)
    research_agent = ResearchAgent()
    life_planning_agent = LifePlanningAgent()
    location_agent = LocationAgent()
    agent = GeneralConversationAgent(
        research_agent.agent, life_planning_agent.agent, location_agent.agent
    )

    if tts_voice:
        from app.models.model_registry import create_tts

        _tts = create_tts(tts_provider or "style-bert-vits2")
    else:
        _tts = tts

    PUNCTUATIONS = {"。", "！", "？", "!", "?"}

    async def event_stream():
        # すべての SSE イベントをここに集約
        event_queue: asyncio.Queue[str] = asyncio.Queue()

        # ---------- Producer 1: テキスト & オーディオ & Ditto への音声 push ----------
        async def text_and_audio_producer():
            sentence_buffer = ""

            async for chunk in agent.stream_generate(user_id="1", message=user_input):
                text_piece = str(chunk)
                sentence_buffer += text_piece

                # テキストチャンクをすぐイベントに
                await event_queue.put(sse_event("text_chunk", {"content": text_piece}))

                # 文末検出 → 1文ぶんを TTS & Ditto へ
                if any(p in text_piece for p in PUNCTUATIONS):
                    current_sentence = sentence_buffer.strip()
                    if not current_sentence:
                        continue

                    # TTS はスレッド側で実行
                    audio_b64 = await asyncio.to_thread(
                        _tts.synthesize_to_base64, current_sentence
                    )

                    # audio_chunk を即イベントキューへ
                    await event_queue.put(
                        sse_event(
                            "audio_chunk",
                            {
                                "sentence": current_sentence,
                                "audio": audio_b64,
                            },
                        )
                    )

                    # Ditto に音声を push（これもスレッド側で）
                    def push_audio():
                        arr = audio_b64_to_array(audio_b64, target_sr=16000)
                        avatar_streamer.push_audio_array(arr, sr=16000)

                    await asyncio.to_thread(push_audio)

                    # 文バッファをリセット
                    sentence_buffer = ""

            # 句読点なしで終わった場合の残りの文
            if sentence_buffer.strip():
                last_sentence = sentence_buffer.strip()
                audio_b64 = await asyncio.to_thread(
                    _tts.synthesize_to_base64, last_sentence
                )

                await event_queue.put(
                    sse_event(
                        "audio_chunk",
                        {"sentence": last_sentence, "audio": audio_b64},
                    )
                )

                def push_audio():
                    arr = audio_b64_to_array(audio_b64, target_sr=16000)
                    avatar_streamer.push_audio_array(arr, sr=16000)

                await asyncio.to_thread(push_audio)

            # もう音声は来ないことを Ditto に通知
            avatar_streamer.signal_end()

        # ---------- Producer 2: Ditto → frame_chunk イベント ----------
        async def frame_producer():
            # generate_frames() はブロッキングなので to_thread で回す
            loop = asyncio.get_running_loop()

            def _run():
                for frame in avatar_streamer.generate_frames():
                    # フレームが 1 枚くるたびにここに入る
                    frame_bgr = frame[:, :, ::-1]
                    ok, buf = cv2.imencode(".jpg", frame_bgr)
                    if not ok:
                        continue
                    img_b64 = base64.b64encode(buf).decode("ascii")

                    ev = sse_event(
                        "frame_chunk",
                        {
                            "image": img_b64,
                        },
                    )
                    # メインスレッドの event_loop 上で event_queue に積む
                    loop.call_soon_threadsafe(event_queue.put_nowait, ev)

            # 実際にスレッド側で _run を実行
            await asyncio.to_thread(_run)

        # Producer タスクを起動
        text_task = asyncio.create_task(text_and_audio_producer())
        frame_task = asyncio.create_task(frame_producer())
        producers = [text_task, frame_task]

        # ---------- メインの SSE ループ ----------
        while True:
            # 両方の producer が終了していて、かつキューが空なら終了
            if all(t.done() for t in producers) and event_queue.empty():
                break

            try:
                # 何かイベントが入るまで待つ（タイムアウトでループ継続）
                ev = await asyncio.wait_for(event_queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                continue

            # ここで 1 イベントずつクライアントへ送信される
            yield ev

        # 最後に完了イベント
        yield sse_event("done", {"message": "応答完了"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
