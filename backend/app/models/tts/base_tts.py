from abc import ABC, abstractmethod


class BaseTTS(ABC):
    """TTS の基底クラス"""

    _model_name: str

    @property
    def model_name(self) -> str:
        """カタログの tts_id に対応する固有キーを返す"""
        return self._model_name

    @abstractmethod
    def synthesize_to_base64(self, text: str) -> str:
        """テキストを音声に変換し、Base64 エンコードした文字列を返す"""
        ...
