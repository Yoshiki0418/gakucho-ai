"""
🎙️ STT モジュールパッケージ
BaseSTT（抽象基底）と WhisperSTT（実装クラス）を提供。
"""

from .base_stt import BaseSTT
from .whisper_stt import WhisperSTT

__all__ = ["BaseSTT", "WhisperSTT"]