import asyncio
import tempfile

import numpy as np
import soundfile as sf
import torch
import whisper

from .base_stt import BaseSTT


class WhisperSTT(BaseSTT):
    """
    🧠 WhisperSTT
    OpenAI Whisper を使用した音声認識クラス。
    """

    def __init__(self, sample_rate: int = 16000, name: str = "base") -> None:
        super().__init__(sample_rate)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisper.load_model(name, device=device)
        self._model_name = f"whisper_{name}"

    # ---------- 音声→テキスト ----------
    async def _transcribe_impl(self, pcm_chunk: bytes) -> str:
        """
        Whisperモデルを使ってPCM音声を文字起こしする。
        非同期対応のため、一時ファイルに保存して処理。
        """
        # PCM → numpy に変換
        audio_np = np.frombuffer(pcm_chunk, dtype=np.int16).astype(np.float32) / 32768.0

        # 一時ファイルに保存（Whisperがwav入力を要求するため）
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmpfile:
            sf.write(tmpfile.name, audio_np, self.sample_rate)

            # Whisper 推論は同期処理なので to_thread で非同期化
            result = await asyncio.to_thread(
                self.model.transcribe, tmpfile.name, language="ja"
            )

        text = result.get("text", "").strip()
        return text


# 動作確認用
# if __name__ == "__main__":
#     async def main():
#         stt = WhisperSTT(name="large")
#         await stt.start()

#         # 例: test.wav を読み込み、チャンクに分割して認識
#         wav_path = "test.wav"
#         chunk_size = 16000 * 5  # 5秒チャンク
#         with open(wav_path, "rb") as f:
#             pcm_data = f.read()

#         for i in range(0, len(pcm_data), chunk_size * 2):  # 16bitなので2倍
#             chunk = pcm_data[i:i + chunk_size * 2]
#             if not chunk:
#                 break
#             await stt.transcribe_audio_chunk(chunk)
#             result = await stt.result_queue.get()
#             print(f"Transcribed Text: {result['text']} (Latency: {result['latency_ms']} ms)")

#         await stt.stop()

#     asyncio.run(main())
