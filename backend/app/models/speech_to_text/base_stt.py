import asyncio
from abc import ABC, abstractmethod
from typing import Any

import numpy as np
from numpy.typing import NDArray


class BaseSTT(ABC):
    """
    🎙️ 音声認識（Speech-to-Text）モジュール共通基底クラス

    各STTモデル（Whisper, OpenAI STTなど）はこのクラスを継承し、
    `_transcribe_impl()` のみを実装すれば動作可能。
    """

    _model_name: str

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate
        self.result_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._silence_trim_duration = 0.05

    # ---------- 初期化・停止 ----------
    async def start(self) -> None:
        print("▶️ STT model ready")

    async def stop(self) -> None:
        print("⛔ STT model stopped")

    # ---------- 音声認識処理 ----------
    @abstractmethod
    async def _transcribe_impl(self, pcm_chunk: bytes) -> str:
        """
        サブクラスで実装する。
        pcm_chunk を入力し、テキスト文字列を返す。
        """
        raise NotImplementedError("Subclasses must implement this method.")

    async def _transcribe_and_measure(self, pcm_chunk: bytes) -> tuple[str, int]:
        """
        内部ユーティリティ:
        音声チャンクをモデルに入力し、文字起こしと処理時間(ms)を取得する。

        Returns:
            tuple[str, int]: (文字起こし結果, レイテンシー[ms])
        """
        start = asyncio.get_event_loop().time()
        text = await self._transcribe_impl(pcm_chunk)
        latency_ms = int((asyncio.get_event_loop().time() - start) * 1000)
        return text, latency_ms

    async def transcribe_audio_chunk(self, pcm_chunk: bytes):
        """
        非同期モード（対話用）:
        - 音声チャンクを認識して result_queue に格納する。
        - WebSocket 対話やリアルタイムSTTで利用。
        - 処理完了を待たずに次の処理を並行実行できる。
        """
        text, latency = await self._transcribe_and_measure(pcm_chunk)
        await self.result_queue.put({"text": text, "latency_ms": latency})

    async def transcribe_once(self, pcm_chunk: bytes) -> dict[str, Any]:
        """
        同期モード（即時変換用）:
        - 音声を入力して、その場で結果を返す。
        - 検索バーやテキスト入力欄のマイク入力など、単発の音声認識に利用。

        Returns:
            dict[str, Any]: {"text": 認識結果, "latency_ms": 処理時間}
        """
        text, latency = await self._transcribe_and_measure(pcm_chunk)
        return {"text": text, "latency_ms": latency}

    # ---------- サイレンストリム ----------
    def _trim_tail_silence(self, np_chunk: NDArray[np.int16]) -> NDArray[np.int16]:
        """末尾の無音部分をカットするユーティリティ"""
        trim = int(self._silence_trim_duration * self.sample_rate)
        return np_chunk[:-trim] if trim and len(np_chunk) > trim else np_chunk

    def set_silence_threshold(self, sec: float) -> None:
        """無音カット閾値（秒）を設定"""
        print(f"⚙️ silence_duration_threshold = {sec:.2f} 秒")
        self._silence_trim_duration = sec

    @property
    def model_name(self) -> str:
        return self._model_name
