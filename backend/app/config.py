"""
アプリケーション設定モジュール。

環境変数の読み込みを一元管理する。
他のモジュールは `from app.config import settings` で設定値にアクセスする。

使い方:
    from app.config import settings
    api_key = settings.OPENAI_API_KEY
"""

import os

from dotenv import load_dotenv

# Docker DevContainer のマウントパスを優先的に探す
_env_path = "/workspace/backend/.env"
if os.path.exists(_env_path):
    load_dotenv(_env_path)
else:
    load_dotenv()  # カレントディレクトリの .env にフォールバック


class _Settings:
    """環境変数を属性として公開する設定クラス"""

    @property
    def OPENAI_API_KEY(self) -> str:
        return os.getenv("OPENAI_API_KEY", "")

    @property
    def DB_URL(self) -> str:
        return os.getenv("DB_URL", "")

    @property
    def HF_TOKEN(self) -> str:
        return os.getenv("HF_TOKEN", "")


settings = _Settings()
