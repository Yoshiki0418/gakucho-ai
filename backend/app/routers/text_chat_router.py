import asyncio

# import base64
# import io
import json
import re
import time

# import cv2
# import numpy as np
# import soundfile as sf
from app.agent.agent_factory import build_conversation_orchestrator
from app.agent.general_conversation.agent import GeneralConversationAgent
from app.agent.general_conversation.domains import (
    LifePlanningAgent,
    LocationAgent,
    ResearchAgent,
)
from app.models import llm, tts
from app.services.history_service import HistoryService

# from app.models.lipsync.ditto_batch_streamer import AvatarStreamer
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

# import queue as sync_queue
# from typing import Dict


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


# CFG_PKL = "/workspace/backend/app/weights/lipsync/ditto_cfg/v0.4_hubert_cfg_pytorch.pkl"
# DATA_ROOT = "/workspace/backend/app/weights/lipsync/ditto_pytorch"
# SOURCE_IMAGE = "test.jpg"


# def audio_b64_to_array(audio_b64: str, target_sr: int = 16000) -> np.ndarray:
#     audio_bytes = base64.b64decode(audio_b64)
#     # soundfile でメモリ上から読む
#     data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
#     if data.ndim == 2:
#         data = data.mean(axis=1)  # stereo → mono
#     if sr != target_sr:
#         import librosa

#         data = librosa.resample(data, orig_sr=sr, target_sr=target_sr)
#         sr = target_sr
#     return data


# def sse_event(event_type: str, payload: dict) -> str:
#     data = {"type": event_type, **payload}
#     return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# async def push_audio_and_stream_frames(
#     audio_b64: str,
#     avatar_streamer: AvatarStreamer,
#     out_queue: "asyncio.Queue[str]",
#     frame_index_state: Dict[str, int],
#     fps: int = 24,
# ):
#     """
#     1文ぶんの音声を Ditto に push し、
#     その時点までに生成されたフレームを frame_chunk として SSEキューに積む。
#     """

#     # 1) 音声を Ditto に投入
#     def _push():
#         arr = audio_b64_to_array(audio_b64, target_sr=16000)
#         avatar_streamer.push_audio_array(arr, sr=16000)

#     await asyncio.to_thread(_push)

#     # 2) 今キューに溜まっているフレームだけ non-blocking で回収
#     frames = []
#     while True:
#         try:
#             frame = avatar_streamer.frame_output_queue.get_nowait()
#         except sync_queue.Empty:
#             break

#         if frame is None:
#             # 終了シグナル
#             break

#         frames.append(frame)

#     # 3) SSE キューに frame_chunk を積む
#     for frame in frames:
#         frame_bgr = frame[:, :, ::-1]
#         ok, buf = cv2.imencode(".jpg", frame_bgr)
#         if not ok:
#             continue
#         img_b64 = base64.b64encode(buf).decode("ascii")

#         idx = frame_index_state["value"]
#         frame_index_state["value"] += 1

#         await out_queue.put(
#             sse_event(
#                 "frame_chunk",
#                 {
#                     "frame_index": idx,
#                     "fps": fps,
#                     "image": img_b64,
#                 },
#             )
#         )


# # --- Ditto / AvatarStreamer のセットアップ ---
# avatar_streamer = AvatarStreamer(
#     CFG_PKL,
#     DATA_ROOT,
#     online_mode=False,  # 先頭フレーム欠損を避けるため False 推奨
#     output_path="dummy.mp4",  # 使わないが必須なら適当でOK
# )
# avatar_streamer.setup(
#     SOURCE_IMAGE,
#     "./dummy_output.mp4",
#     online_mode=False,
# )


# @router.get("/char-stream-agent-avatar")
# async def char_stream_agent_avatar(request: Request):
#     user_input = request.query_params.get("text", "こんにちは！")

#     # --- Agent / TTS の準備 ---
#     tts_provider = request.query_params.get("tts_provider", None)
#     tts_voice = request.query_params.get("tts_voice", None)

#     if tts_voice:
#         from app.models.model_registry import create_tts

#         _tts = create_tts(tts_provider or "style-bert-vits2")
#     else:
#         _tts = tts

#     PUNCTUATIONS = {"。", "！", "？", "!", "?"}
#     FPS = 25  # Dittoのフレームレート

#     async def event_stream():
#         sentence_buffer = ""

#         async for chunk in conversation_orchestrator.stream_response(user_id="1", text=user_input):
#             text_piece = str(chunk)
#             sentence_buffer += text_piece

#             # テキストチャンクをすぐイベントに
#             yield sse_event("text_chunk", {"content": text_piece})

#             # 文末検出 → 1文ぶんを TTS & リップシンク同時処理
#             if any(p in text_piece for p in PUNCTUATIONS):
#                 current_sentence = sentence_buffer.strip()
#                 if not current_sentence:
#                     continue

#                 # 同期的に TTS + リップシンクを処理
#                 def process_sentence():
#                     # 1. TTS で音声生成
#                     audio_b64 = _tts.synthesize_to_base64(current_sentence)

#                     # 2. 音声をnumpy arrayに変換
#                     audio_array = audio_b64_to_array(audio_b64, target_sr=16000)

#                     # 3. リップシンクフレーム生成 (全フレーム待機)
#                     frames = avatar_streamer.generate_frames_for_audio(audio_array, sr=16000)

#                     # 4. フレームをbase64エンコード
#                     frames_b64 = []
#                     for frame in frames:
#                         frame_bgr = frame[:, :, ::-1]
#                         ok, buf = cv2.imencode(".jpg", frame_bgr)
#                         if ok:
#                             frames_b64.append(base64.b64encode(buf).decode("ascii"))

#                     return audio_b64, frames_b64

#                 audio_b64, frames_b64 = await asyncio.to_thread(process_sentence)

#                 # 音声とフレームを一緒に送信
#                 yield sse_event(
#                     "audio_and_frames",
#                     {
#                         "sentence": current_sentence,
#                         "audio": audio_b64,
#                         "frames": frames_b64,
#                         "fps": FPS,
#                     },
#                 )

#                 # 文バッファをリセット
#                 sentence_buffer = ""

#         # 句読点なしで終わった場合の残りの文
#         if sentence_buffer.strip():
#             last_sentence = sentence_buffer.strip()

#             def process_last_sentence():
#                 audio_b64 = _tts.synthesize_to_base64(last_sentence)
#                 audio_array = audio_b64_to_array(audio_b64, target_sr=16000)
#                 frames = avatar_streamer.generate_frames_for_audio(audio_array, sr=16000)

#                 frames_b64 = []
#                 for frame in frames:
#                     frame_bgr = frame[:, :, ::-1]
#                     ok, buf = cv2.imencode(".jpg", frame_bgr)
#                     if ok:
#                         frames_b64.append(base64.b64encode(buf).decode("ascii"))

#                 return audio_b64, frames_b64

#             audio_b64, frames_b64 = await asyncio.to_thread(process_last_sentence)

#             yield sse_event(
#                 "audio_and_frames",
#                 {
#                     "sentence": last_sentence,
#                     "audio": audio_b64,
#                     "frames": frames_b64,
#                     "fps": FPS,
#                 },
#             )

#         # 最後に完了イベント
#         yield sse_event("done", {"message": "応答完了"})

#     return StreamingResponse(event_stream(), media_type="text/event-stream")


conversation_orchestrator = build_conversation_orchestrator()

# --- 対話履歴サービスの初期化 ---
try:
    history_service = HistoryService()
except Exception as e:
    print(f"[WARNING] HistoryService の初期化に失敗しました: {e}")
    history_service = None

# --- 音声出力用テキスト浄化 ---
_RE_URL = re.compile(r"https?://\S+")
_RE_PAREN_DOMAIN = re.compile(r"\s*\([a-zA-Z0-9\-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?\)")
_RE_MD_LINK = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
_RE_MD_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_RE_MD_BULLET = re.compile(r"^\s*[-*]\s+", re.MULTILINE)


def _sanitize_for_speech(text: str) -> str:
    """音声読み上げ向けにURL・出典・マークダウンを除去する"""
    text = _RE_URL.sub("", text)
    text = _RE_PAREN_DOMAIN.sub("", text)
    text = _RE_MD_LINK.sub(r"\1", text)
    text = _RE_MD_BOLD.sub(r"\1", text)
    text = _RE_MD_BULLET.sub("", text)
    # 連続空白・改行を圧縮
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"  +", " ", text)
    return text


@router.get("/char-stream-orchestrator")
async def char_stream_orchestrator(request: Request):
    t0 = time.perf_counter()  # === 計測開始 ===
    user_input = request.query_params.get("text", "こんにちは！")
    user_id = request.query_params.get("user_id", "default")
    session_id = request.query_params.get("session_id", "default")

    # --- 対話履歴の取得 ---
    history = []
    if history_service:
        try:
            history = history_service.get_recent_history(
                user_id=user_id, session_id=session_id, n=10
            )
        except Exception as e:
            print(f"[WARNING] 履歴取得に失敗: {e}")
            history = []

    # --- ユーザーメッセージの保存 ---
    if history_service:
        try:
            history_service.save_message(
                user_id=user_id,
                session_id=session_id,
                role="user",
                content=user_input,
            )
        except Exception as e:
            print(f"[WARNING] ユーザーメッセージ保存に失敗: {e}")

    # モデル選択
    tts_provider = request.query_params.get("tts_provider", None)
    tts_voice = request.query_params.get("tts_voice", None)

    if tts_voice:
        from app.models.model_registry import create_tts

        _tts = create_tts(tts_provider or "style-bert-vits2")
    else:
        _tts = tts

    PUNCTUATIONS = {"。", "！", "？", "!", "?"}

    async def event_stream():
        sentence_buffer = ""
        full_response = ""  # アシスタント応答全文を蓄積
        first_text_logged = False
        first_audio_logged = False

        async for chunk in conversation_orchestrator.stream_response(
            user_id=user_id,
            text=user_input,
            history=history,
        ):
            raw_piece = str(chunk)
            sentence_buffer += raw_piece

            # --- 初回テキストチャンクの計測 ---
            if not first_text_logged:
                ttft = (time.perf_counter() - t0) * 1000
                print(f"[TIMING] TTFT (Time To First Text): {ttft:.0f}ms")
                first_text_logged = True

            # 文の終端を検出したら、完成した文をサニタイズして出力
            if any(p in raw_piece for p in PUNCTUATIONS):
                raw_sentence_for_metadata = sentence_buffer.strip()

                # --- URLを抽出してメタデータとして送信 ---
                # "www." または "http(s)://" から始まり、改行などで途切れるまでを抽出
                _url_regex = re.compile(
                    r"(https?://[^\s()（）「」]+|www\.[^\s()（）「」]+)"
                )
                urls = _url_regex.findall(raw_sentence_for_metadata)
                if urls:
                    for url in urls:
                        # 句読点などが末尾についていれば除去
                        clean_url = re.sub(r"[。！？!?()（）「」]+$", "", url)
                        yield (
                            "data: "
                            + json.dumps(
                                {
                                    "type": "metadata_chunk",
                                    "dataType": "url",
                                    "content": clean_url,
                                }
                            )
                            + "\n\n"
                        )

                # 文全体に対してサニタイズ（URL・出典を確実に除去）
                current_sentence = _sanitize_for_speech(raw_sentence_for_metadata)
                if not current_sentence:
                    sentence_buffer = ""
                    continue

                full_response += current_sentence

                # テキストを送信
                yield (
                    "data: "
                    + json.dumps({"type": "text_chunk", "content": current_sentence})
                    + "\n\n"
                )

                # 並列で音声生成
                audio_b64 = await asyncio.to_thread(
                    _tts.synthesize_to_base64,
                    current_sentence,
                )

                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "audio_chunk",
                            "sentence": current_sentence,
                            "audio": audio_b64,
                        }
                    )
                    + "\n\n"
                )

                # --- 初回音声チャンクの計測 ---
                if not first_audio_logged:
                    ttfa = (time.perf_counter() - t0) * 1000
                    print(f"[TIMING] TTFA (Time To First Audio): {ttfa:.0f}ms")
                    first_audio_logged = True

                sentence_buffer = ""

        # 最後に残った文を処理
        if sentence_buffer.strip():
            raw_sentence_for_metadata = sentence_buffer.strip()

            # --- URLを抽出してメタデータとして送信 ---
            _url_regex = re.compile(
                r"(https?://[^\s()（）「」]+|www\.[^\s()（）「」]+)"
            )
            urls = _url_regex.findall(raw_sentence_for_metadata)
            if urls:
                for url in urls:
                    clean_url = re.sub(r"[。！？!?()（）「」]+$", "", url)
                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "metadata_chunk",
                                "dataType": "url",
                                "content": clean_url,
                            }
                        )
                        + "\n\n"
                    )

            current_sentence = _sanitize_for_speech(raw_sentence_for_metadata)
            if current_sentence:
                full_response += current_sentence
                yield (
                    "data: "
                    + json.dumps({"type": "text_chunk", "content": current_sentence})
                    + "\n\n"
                )
                audio_b64 = await asyncio.to_thread(
                    _tts.synthesize_to_base64,
                    current_sentence,
                )
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "audio_chunk",
                            "sentence": current_sentence,
                            "audio": audio_b64,
                        }
                    )
                    + "\n\n"
                )

        # --- アシスタント応答の保存 ---
        if history_service and full_response.strip():
            try:
                history_service.save_message(
                    user_id=user_id,
                    session_id=session_id,
                    role="assistant",
                    content=full_response.strip(),
                )
            except Exception as e:
                print(f"[WARNING] アシスタント応答保存に失敗: {e}")

        # --- タイミング情報の送信 ---
        total_ms = (time.perf_counter() - t0) * 1000
        print(f"[TIMING] Total response time: {total_ms:.0f}ms")
        yield (
            "data: "
            + json.dumps(
                {
                    "type": "timing",
                    "total_ms": round(total_ms),
                }
            )
            + "\n\n"
        )

        yield ("data: " + json.dumps({"type": "done", "message": "応答完了"}) + "\n\n")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
