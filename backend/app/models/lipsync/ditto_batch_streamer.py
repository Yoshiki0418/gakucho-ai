import queue

import librosa
import numpy as np

# import元のファイル名は環境に合わせてください
# 例: from inference import StreamSDK
# ここではご提示いただいた名前を使用します
from app.third_party.ditto_talkinghead.stream_pipeline_online import StreamSDK


class AvatarStreamer(StreamSDK):
    """
    Ditto Talking Headのリアルタイム推論用ラッパー
    """

    def __init__(self, cfg_pkl, data_root, **kwargs):
        super().__init__(cfg_pkl, data_root, **kwargs)
        # 生成フレームを一時的に貯めるキュー
        self.frame_output_queue = queue.Queue(maxsize=100)
        self.is_streaming_finished = False

    def _writer_worker(self):
        """
        [Override] ファイル書き出しを無効化し、メモリ上のキューに出力する
        """
        while not self.stop_event.is_set():
            try:
                # 前段(PutBack)からフレームを取得
                item = self.writer_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            if item is None:
                # 終了シグナル
                self.frame_output_queue.put(None)
                break

            # キューがいっぱいなら空くまで待機（データロスト防止）
            while not self.stop_event.is_set():
                try:
                    self.frame_output_queue.put(item, timeout=0.05)
                    break
                except queue.Full:
                    continue

            if hasattr(self, "writer_pbar"):
                self.writer_pbar.update()

    def push_audio_array(self, speech_array, sr=16000):
        """
        波形データ(numpy array)を直接受け取ってパイプラインに流す
        """
        # 特徴量抽出 (wav2feat)
        aud_feat = self.wav2feat.wav2feat(speech_array, sr=sr)
        # 推論キューへ投入
        self.audio2motion_queue.put(aud_feat)

    def push_audio_file(self, audio_path):
        """
        音声ファイルをロードしてパイプラインに流す
        """
        # 16kHzでロード
        speech, sr = librosa.load(audio_path, sr=16000)
        self.push_audio_array(speech, sr)

    def push_silence(self, duration_sec=1.0):
        """
        指定秒数の無音データを送る。
        """
        sr = 16000
        # 無音（ゼロ）の配列を作成
        silence_array = np.zeros(int(sr * duration_sec), dtype=np.float32)
        self.push_audio_array(silence_array, sr)

    def signal_end(self):
        """ストリーミング終了を通知"""
        self.audio2motion_queue.put(None)
        self.is_streaming_finished = True

    def generate_frames(self):
        """
        生成されたフレームを逐次yieldするジェネレータ
        """
        first_frame_received = False

        while True:
            try:
                # 初回の1枚目が来るまでは、モデルのロードや初期推論で時間がかかるため長く待つ
                timeout = 10.0 if not first_frame_received else 0.1

                frame = self.frame_output_queue.get(timeout=timeout)
            except queue.Empty:
                # 処理が完了しており、かつキューも空なら終了
                if self.is_streaming_finished and self.writer_queue.empty():
                    break
                # まだ処理中なら待機継続
                continue

            if frame is None:
                break

            first_frame_received = True
            yield frame

    def generate_frames_for_audio(
        self, audio_array: np.ndarray, sr: int = 16000
    ) -> list:
        """
        音声データを入力し、対応するリップシンクフレームを全て生成して返す。
        同期的に処理し、フレームがすべて生成されてからリストとして返す。

        注意: この関数は終了シグナルを送らないため、複数回呼び出し可能。

        Args:
            audio_array: 16kHz float32 音声波形
            sr: サンプリングレート (default: 16000)

        Returns:
            list[np.ndarray]: 生成されたフレームのリスト
        """
        import time

        # 音声の長さからフレーム数を推定 (fps=25で計算)
        fps = 25
        audio_duration = len(audio_array) / sr
        expected_frames = int(audio_duration * fps)

        if expected_frames == 0:
            return []

        # 音声をパイプラインに投入（終了シグナルは送らない）
        self.push_audio_array(audio_array, sr)

        frames = []
        start_time = time.time()
        max_wait_time = audio_duration + 5.0  # 音声長 + バッファ時間

        while len(frames) < expected_frames:
            try:
                # タイムアウトを短めにしてポーリング
                frame = self.frame_output_queue.get(timeout=0.1)
            except queue.Empty:
                # 最大待機時間を超えたら終了
                if time.time() - start_time > max_wait_time:
                    break
                continue

            if frame is None:
                # 終了シグナルを受け取った場合はキューに戻して終了
                # （他の処理が終了シグナルを必要とする場合のため）
                self.frame_output_queue.put(None)
                break

            frames.append(frame)

        return frames

    def stream_frames_for_audio(self, audio_array: np.ndarray, sr: int = 16000):
        """
        音声データを入力し、対応するリップシンクフレームを逐次yieldするジェネレータ。

        Args:
            audio_array: 16kHz float32 音声波形
            sr: サンプリングレート (default: 16000)

        Yields:
            np.ndarray: 生成されたフレーム
        """
        import time

        # 音声の長さからフレーム数を推定 (fps=25で計算)
        fps = 25
        audio_duration = len(audio_array) / sr
        expected_frames = int(audio_duration * fps)

        if expected_frames == 0:
            return

        # 音声をパイプラインに投入（終了シグナルは送らない）
        self.push_audio_array(audio_array, sr)

        frames_count = 0
        start_time = time.time()
        max_wait_time = audio_duration + 5.0  # 音声長 + バッファ時間

        while frames_count < expected_frames:
            try:
                # タイムアウトを短めにしてポーリング
                frame = self.frame_output_queue.get(timeout=0.1)
            except queue.Empty:
                # 最大待機時間を超えたら終了
                if time.time() - start_time > max_wait_time:
                    break
                continue

            if frame is None:
                # 終了シグナルを受け取った場合はキューに戻して終了
                self.frame_output_queue.put(None)
                break

            yield frame
            frames_count += 1
