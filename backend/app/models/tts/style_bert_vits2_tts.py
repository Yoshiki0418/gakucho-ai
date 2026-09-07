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
from style_bert_vits2.models import commons
from style_bert_vits2.nlp import clean_text
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
            length=1.1,
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

    @staticmethod
    def _phone_to_viseme(phone: str) -> str:
        """Style-Bert-VITS2 の日本語音素を口形へまとめる。"""
        p = phone.lower()
        if p in {"a", "i", "u", "e", "o"}:
            return p.upper()
        if p in {"p", "b", "m"} or phone == "N":
            return "M"
        if p in {"f", "v"}:
            return "F"
        if p in {"s", "z", "sh", "j", "ch", "ts"}:
            return "S"
        if p in {"t", "d", "n", "r"}:
            return "T"
        if p in {"k", "g", "h"}:
            return "K"
        if p == "w":
            return "U"
        if p == "y":
            return "I"
        return "sil"

    def synthesize_with_visemes_to_base64(self, text: str) -> dict:
        """音声と、同じ推論で得た音素境界に基づくビセーム列を返す。

        VITS の duration predictor が生成に実際に使用した alignment を使うため、
        文字数による均等割りではなく、生成された発話の子音・母音長に一致する。
        """
        if not text.strip():
            raise ValueError("入力テキストが空です。")

        model = self.tts_model
        hps = model.hyper_parameters
        net_g = model._TTSModel__net_g
        if net_g is None:
            model.load()
            net_g = model._TTSModel__net_g
        if net_g is None:
            raise RuntimeError("TTS model is not loaded")

        use_jp_extra = hps.version.endswith("JP-Extra")
        _, phone_names, _, _ = clean_text(
            text,
            Languages.JP,
            use_jp_extra=use_jp_extra,
            raise_yomi_error=False,
        )

        bert, ja_bert, en_bert, phones, tones, lang_ids = infer_module.get_text(
            text,
            Languages.JP,
            hps,
            model.device,
        )
        if hps.data.add_blank:
            # VITS が音素間に挿入する blank は無音ではなく、前後の音素をつなぐ
            # 潜在フレーム。句読点や先頭末尾の本当の無音とは区別する。
            phone_names = commons.intersperse(phone_names, None)

        style_id = model.style2id["Neutral"]
        style_vector = model._TTSModel__get_style_vector(style_id, 1.0)

        with torch.no_grad():
            x_tst = phones.to(model.device).unsqueeze(0)
            tone_tensor = tones.to(model.device).unsqueeze(0)
            language_tensor = lang_ids.to(model.device).unsqueeze(0)
            ja_bert_tensor = ja_bert.to(model.device).unsqueeze(0)
            x_tst_lengths = torch.LongTensor([phones.size(0)]).to(model.device)
            style_tensor = torch.from_numpy(style_vector).to(model.device).unsqueeze(0)
            sid_tensor = torch.LongTensor([0]).to(model.device)

            if use_jp_extra:
                output = net_g.infer(
                    x_tst,
                    x_tst_lengths,
                    sid_tensor,
                    tone_tensor,
                    language_tensor,
                    ja_bert_tensor,
                    style_vec=style_tensor,
                    sdp_ratio=DEFAULT_SDP_RATIO,
                    noise_scale=DEFAULT_NOISE,
                    noise_scale_w=DEFAULT_NOISEW,
                    length_scale=1.1,
                )
            else:
                output = net_g.infer(
                    x_tst,
                    x_tst_lengths,
                    sid_tensor,
                    tone_tensor,
                    language_tensor,
                    bert.to(model.device).unsqueeze(0),
                    ja_bert_tensor,
                    en_bert.to(model.device).unsqueeze(0),
                    style_vec=style_tensor,
                    sdp_ratio=DEFAULT_SDP_RATIO,
                    noise_scale=DEFAULT_NOISE,
                    noise_scale_w=DEFAULT_NOISEW,
                    length_scale=1.1,
                )

        audio = output[0][0, 0].detach().cpu().float().numpy()
        alignment = output[1][0, 0].detach().cpu().float().numpy()
        durations = alignment.sum(axis=0)
        if len(phone_names) != len(durations):
            raise RuntimeError(
                "TTS alignment length mismatch: "
                f"phones={len(phone_names)}, durations={len(durations)}"
            )
        audio = model._TTSModel__convert_to_16_bit_wav(audio)
        sr = hps.data.sampling_rate
        audio_duration = len(audio) / float(sr)

        # alignment は音声フレーム単位なので、実際のWAV長へ比例変換する。
        total_frames = float(durations.sum()) or 1.0
        cursor = 0.0
        raw_frames = []
        base_visemes = [
            self._phone_to_viseme(phone) if phone is not None else None
            for phone in phone_names
        ]
        for index, (phone, frame_count) in enumerate(zip(phone_names, durations)):
            start = cursor / total_frames * audio_duration
            cursor += float(frame_count)
            end = cursor / total_frames * audio_duration
            viseme = base_visemes[index]
            if viseme is None:
                previous = next(
                    (v for v in reversed(base_visemes[:index]) if v not in (None, "sil")),
                    None,
                )
                following = next(
                    (v for v in base_visemes[index + 1 :] if v not in (None, "sil")),
                    None,
                )
                # 口形は少し先行するため、次の音素があればそちらへ寄せる。
                viseme = following or previous or "sil"
            if end - start < 0.004:
                continue
            raw_frames.append({"start": start, "end": end, "viseme": viseme})

        # 連続する同じ口形をまとめ、通信量とUE側の更新回数を抑える。
        visemes = []
        for frame in raw_frames:
            if visemes and visemes[-1]["viseme"] == frame["viseme"]:
                visemes[-1]["end"] = frame["end"]
            else:
                visemes.append(frame)

        buffer = io.BytesIO()
        sf.write(buffer, audio, sr, format="WAV")
        audio_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return {
            "audio": audio_b64,
            "visemes": visemes,
            "duration": audio_duration,
        }
