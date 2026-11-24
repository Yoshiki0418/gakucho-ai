"""Bounded, opt-in transcription using Whisper checkpoints already on disk.

Catalog reads do not import Torch, load a model, or download weights. The browser
engine is handled entirely in the browser; only explicit Whisper requests reach
this service.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import threading
from pathlib import Path

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_AUDIO_SECONDS = 60
SAMPLE_RATE = 16000
WHISPER_NAMES = ("tiny", "base", "small", "large-v3-turbo", "large-v3")
_inference_lock = threading.Lock()
_loaded_model = None
_loaded_key = None


class SpeechSettingsError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _cache_dir() -> Path:
    default = Path(os.getenv("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "whisper"
    return Path(os.getenv("WHISPER_CACHE_DIR", str(default)))


def _enabled_names() -> set[str]:
    return {
        name.strip()
        for name in os.getenv("WHISPER_MODELS", "base,large-v3-turbo").split(",")
        if name.strip() in WHISPER_NAMES
    }


def get_stt_options() -> list[dict]:
    """Expose readiness, including a reason when a server model is unavailable."""
    options = [{"id": "browser", "label": "ブラウザの音声認識", "available": True}]
    has_whisper = importlib.util.find_spec("whisper") is not None
    has_decoder = shutil.which("ffmpeg") is not None
    enabled = _enabled_names()
    for name in WHISPER_NAMES:
        reason = None
        if name not in enabled:
            reason = "このサーバーでは有効になっていません"
        elif not has_whisper or not has_decoder:
            reason = "サーバーの音声認識機能が未準備です"
        elif not (_cache_dir() / f"{name}.pt").is_file():
            reason = "音声モデルがサーバーに配置されていません"
        option = {
            "id": f"whisper-{name}",
            "label": f"Whisper {name}",
            "available": reason is None,
        }
        if reason:
            option["reason"] = reason
        options.append(option)
    return options


def validate_whisper_model(model_id: str) -> Path:
    # Resolve only known identifiers, never an uploaded filename or client path.
    options = {option["id"]: option for option in get_stt_options()}
    option = options.get(model_id)
    if option is None or model_id == "browser":
        raise SpeechSettingsError("利用できるWhisperモデルを選択してください。")
    if not option["available"]:
        raise SpeechSettingsError(option["reason"], 503)
    return _cache_dir() / f"{model_id.removeprefix('whisper-')}.pt"


def decode_audio(payload: bytes):
    """Decode at most 61 seconds; reject anything exceeding the 60-second limit."""
    import numpy as np

    if not payload:
        raise SpeechSettingsError("録音データが空です。")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise SpeechSettingsError("音声ファイルは8 MiB以下にしてください。", 413)
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-protocol_whitelist",
                "pipe",
                "-i",
                "pipe:0",
                "-vn",
                "-t",
                str(MAX_AUDIO_SECONDS + 1),
                "-ac",
                "1",
                "-ar",
                str(SAMPLE_RATE),
                "-f",
                "f32le",
                "pipe:1",
            ],
            input=payload,
            capture_output=True,
            timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SpeechSettingsError(
            "音声の読み込みがタイムアウトしました。", 422
        ) from exc
    except OSError as exc:
        raise SpeechSettingsError(
            "サーバーの音声デコーダーが利用できません。", 503
        ) from exc
    if result.returncode or not result.stdout or len(result.stdout) % 4:
        raise SpeechSettingsError("音声ファイルを読み込めませんでした。", 422)
    audio = np.frombuffer(result.stdout, dtype=np.float32)
    if len(audio) > MAX_AUDIO_SECONDS * SAMPLE_RATE:
        raise SpeechSettingsError("録音は60秒以内にしてください。", 413)
    if not np.isfinite(audio).all():
        raise SpeechSettingsError("音声データが不正です。", 422)
    return audio.copy()


def transcribe_audio(payload: bytes, model_id: str) -> str:
    """Serialize model loading/inference without modifying another user's model."""
    global _loaded_key, _loaded_model
    checkpoint = validate_whisper_model(model_id)
    if not _inference_lock.acquire(blocking=False):
        raise SpeechSettingsError(
            "音声認識が処理中です。少し待って再度お試しください。", 429
        )
    try:
        audio = decode_audio(payload)
        import whisper

        # A path (not a model name) guarantees whisper.load_model cannot download.
        device = os.getenv("WHISPER_DEVICE", "cpu")
        key = (str(checkpoint), checkpoint.stat().st_mtime_ns, device)
        if _loaded_key != key:
            _loaded_model = None
            _loaded_key = None
            _loaded_model = whisper.load_model(str(checkpoint), device=device)
            _loaded_key = key
        result = _loaded_model.transcribe(
            audio,
            language="ja",
            fp16=device.startswith("cuda"),
            verbose=False,
            condition_on_previous_text=False,
        )
        return str(result.get("text", "")).strip()
    finally:
        _inference_lock.release()
