import base64
import io
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

# Monkeypatching: style_bert_vits2.models.infer.get_text
# 理由: 最新環境で BERT モデルが FP16 (Half) で出力を返すようになり、
# Linear レイヤー (Float) との型不整合で RuntimeError が発生するため。
# ここで明示的に float() にキャストするラッパーを差し込む。
import style_bert_vits2.models.infer as infer_module
import style_bert_vits2.nlp.bert_models as bert_models
import torch
from style_bert_vits2.constants import (
    DEFAULT_LENGTH,
    DEFAULT_NOISE,
    DEFAULT_NOISEW,
    DEFAULT_SDP_RATIO,
    Languages,
)
from style_bert_vits2.tts_model import TTSModel

from .base_tts import BaseTTS

_original_get_text = infer_module.get_text


def _get_text_patched(*args, **kwargs):
    bert, ja_bert, en_bert, phone, tone, language = _original_get_text(*args, **kwargs)
    return (
        bert.float(),
        ja_bert.float(),
        en_bert.float(),
        phone,
        tone,
        language,
    )


infer_module.get_text = _get_text_patched


class StyleBertVITS2_TTS(BaseTTS):
    """Style-Bert-VITS2 を用いた日本語TTSクラス"""

    _model_name = "style-bert-vits2"

    def __init__(
        self,
        model_dir: str,
        device: Optional[str] = None,
        weight_name: Optional[str] = None,
    ):
        model_dir = Path(model_dir)
        config_path = model_dir / "config.json"
        style_vec_path = model_dir / "style_vectors.npy"

        if weight_name is not None:
            model_path = model_dir / weight_name
        else:
            # G_*.pth が複数ある場合は最新（更新日時順）を自動選択
            ckpts = sorted(
                model_dir.glob("G_*.pth"), key=lambda p: p.stat().st_mtime, reverse=True
            )
            if not ckpts:
                raise FileNotFoundError(f"{model_dir} 内に G_*.pth が見つかりません。")
            model_path = ckpts[0]

        for path in [model_path, config_path, style_vec_path]:
            if not path.exists():
                raise FileNotFoundError(f"モデルファイルが見つかりません: {path}")

        # ========== デバイス設定 ==========
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        # ========== BERT トークナイザ設定 ==========
        self._setup_bert_tokenizer()

        # ========== モデルロード ==========
        self.tts_model = TTSModel(
            model_path=model_path,
            config_path=config_path,
            style_vec_path=style_vec_path,
            device=device,
        )
        self.tts_model.load()

    def _setup_bert_tokenizer(self):
        """日本語用DeBERTaトークナイザのパスを明示設定"""
        try:
            tokenizer_path = Path(
                "/usr/local/lib/python3.10/dist-packages/style_bert_vits2/bert/deberta-v2-large-japanese-char-wwm"
            )
            bert_models.DEFAULT_BERT_TOKENIZER_PATHS[Languages.JP] = tokenizer_path
        except Exception as e:
            print(f"[警告] BERTトークナイザ設定に失敗: {e}")

    # ========== 音声生成共通ロジック ==========
    def _synthesize(self, text: str) -> tuple[int, np.ndarray]:
        """内部処理：音声波形を生成"""
        if not text.strip():
            raise ValueError("入力テキストが空です。")

        sr, audio = self.tts_model.infer(
            text=text,
            language=Languages.JP,
            speaker_id=0,
            sdp_ratio=DEFAULT_SDP_RATIO,
            noise=DEFAULT_NOISE,
            noise_w=DEFAULT_NOISEW,
            length=DEFAULT_LENGTH,
        )
        return sr, audio

    # ========== 出力：ファイル書き出し ==========
    def generate(self, text: str, output_path: str) -> Path:
        sr, audio = self._synthesize(text)
        sf.write(output_path, audio, sr)
        print(f"[TTS] 生成完了: {output_path}")
        return Path(output_path)

    # ========== 出力：Base64エンコード ==========
    def synthesize_to_base64(self, text: str) -> str:
        sr, audio = self._synthesize(text)
        buffer = io.BytesIO()
        sf.write(buffer, audio, sr, format="WAV")
        buffer.seek(0)
        b64_str = base64.b64encode(buffer.read()).decode("utf-8")
        return b64_str
