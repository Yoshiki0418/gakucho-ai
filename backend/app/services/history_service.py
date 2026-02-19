"""
対話履歴の永続化サービス (psycopg2)
"""

from __future__ import annotations

import os
from typing import Optional

import psycopg2
from dotenv import load_dotenv

load_dotenv()

# デフォルトの取得件数
DEFAULT_HISTORY_LIMIT = 10


class HistoryService:
    """
    conversation_history テーブルに対する CRUD 操作を提供する。
    既存プロジェクトの psycopg2 パターンに合わせた軽量実装。
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("DB_URL")
        if not self.db_url:
            raise RuntimeError(
                "DB_URL が設定されていません。.env に書くか環境変数を渡してください。"
            )
        self.conn = psycopg2.connect(self.db_url)
        self.conn.autocommit = True
        self._ensure_table()

    # ------------------------------------------------------------------
    # テーブル自動作成（初回起動対応）
    # ------------------------------------------------------------------
    def _ensure_table(self) -> None:
        """テーブルが存在しなければ作成する。"""
        sql = """
        CREATE TABLE IF NOT EXISTS conversation_history (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            session_id VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_conv_hist_session
        ON conversation_history (user_id, session_id, created_at DESC);
        """
        with self.conn.cursor() as cur:
            cur.execute(sql)

    # ------------------------------------------------------------------
    # 履歴取得
    # ------------------------------------------------------------------
    def get_recent_history(
        self,
        user_id: str,
        session_id: str,
        n: int = DEFAULT_HISTORY_LIMIT,
    ) -> list[dict]:
        """
        直近 n 件の対話履歴を古い順で返す。
        OpenAI Agents SDK の input 形式 (list[dict]) に合わせた形式。
        """
        sql = """
        SELECT role, content
        FROM conversation_history
        WHERE user_id = %s AND session_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (user_id, session_id, n))
            rows = cur.fetchall()

        # DESC で取得しているので逆順にして古い順に並べる
        rows.reverse()
        return [{"role": row[0], "content": row[1]} for row in rows]

    # ------------------------------------------------------------------
    # メッセージ保存
    # ------------------------------------------------------------------
    def save_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """1 メッセージを保存する。"""
        sql = """
        INSERT INTO conversation_history (user_id, session_id, role, content)
        VALUES (%s, %s, %s, %s)
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (user_id, session_id, role, content))

    # ------------------------------------------------------------------
    # セッション削除（オプション）
    # ------------------------------------------------------------------
    def clear_session(self, user_id: str, session_id: str) -> None:
        """指定セッションの履歴を全削除する。"""
        sql = """
        DELETE FROM conversation_history
        WHERE user_id = %s AND session_id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (user_id, session_id))

    # ------------------------------------------------------------------
    # 終了処理
    # ------------------------------------------------------------------
    def close(self) -> None:
        self.conn.close()
