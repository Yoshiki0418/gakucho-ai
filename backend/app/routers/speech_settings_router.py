"""Uploaded recordings for explicitly selected, locally installed STT models."""

import asyncio
import logging

from app.services.speech_settings import (
    MAX_UPLOAD_BYTES,
    SpeechSettingsError,
    transcribe_audio,
    validate_whisper_model,
)
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

router = APIRouter(prefix="/api/speech", tags=["Speech"])
logger = logging.getLogger(__name__)


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...), model: str = Form(...)):
    try:
        validate_whisper_model(model)
        # Bound the materialized recording; do not save uploads or transcripts.
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise SpeechSettingsError("音声ファイルは8 MiB以下にしてください。", 413)
        if not data:
            raise SpeechSettingsError("録音データが空です。")
        text = await asyncio.to_thread(transcribe_audio, data, model)
        return {"text": text, "model": model}
    except SpeechSettingsError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        # Model/backend details can contain local paths; return a stable message.
        logger.warning("Speech transcription failed (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=503, detail="音声認識を完了できませんでした。"
        ) from exc
    finally:
        await file.close()
