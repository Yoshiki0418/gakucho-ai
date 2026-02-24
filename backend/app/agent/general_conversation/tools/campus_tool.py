"""
キャンパス案内ツール — pgvector RAG で学内施設を検索
金沢工業大学キャンパス内の建物・教室・施設の情報を
RAG (pgvector) から検索して返します。
"""

import json
import os
from typing import Any

import psycopg2
import torch
import torch.nn.functional as F
from agents import function_tool
from sentence_transformers import SentenceTransformer

# =========================================================
# キャンパス検索用 Retriever（軽量版）
# =========================================================
_conn = None
_model = None
_device = None

# キャンパスデータの source 名（CSV取り込み時に指定する名前）
CAMPUS_SOURCE = "campus_map"


def _get_conn():
    """DB接続を遅延初期化で取得"""
    global _conn
    if _conn is None or _conn.closed:
        db_url = os.getenv("DB_URL")
        if not db_url:
            raise RuntimeError("DB_URL が設定されていません。")
        _conn = psycopg2.connect(db_url)
        _conn.autocommit = True
    return _conn


def _get_model():
    """埋め込みモデルを遅延初期化で取得"""
    global _model, _device
    if _model is None:
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = SentenceTransformer("cl-nagoya/ruri-v3-310m")
    return _model, _device


def _embed(text: str) -> list[float]:
    """テキストを正規化済みベクトルに変換"""
    model, device = _get_model()
    emb = model.encode([text], convert_to_tensor=True, device=device)
    emb = F.normalize(emb, p=2, dim=1)
    return emb[0].cpu().tolist()


def _search_campus_db(
    query: str,
    top_k: int = 3,
    threshold: float = 0.20,
) -> list[dict[str, Any]]:
    """
    pgvector でキャンパス情報を検索。
    source='campus_map' のレコードのみを対象とする。
    """
    conn = _get_conn()
    emb = _embed(f"検索クエリ: {query}")

    sql = """
        SELECT id, context, source,
               1 - (embedding <=> %s::vector) AS sim
        FROM ohsawa_context
        WHERE source = %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """

    with conn.cursor() as cur:
        cur.execute(sql, (emb, CAMPUS_SOURCE, emb, top_k))
        rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "context": r[1],
            "source": r[2],
            "similarity": float(r[3]),
        }
        for r in rows
        if float(r[3]) >= threshold
    ]


# =========================================================
# 公開ツール
# =========================================================
@function_tool
def search_campus(query: str) -> str:
    """
    金沢工業大学キャンパス内の施設・建物・教室・窓口などを検索します。
    学内の場所に関する質問に使います。

    使用例:
    - 「食堂はどこ？」
    - 「図書館の場所を教えて」
    - 「1号館の3階には何がある？」
    - 「学生課はどこにある？」
    - 「ATMはキャンパス内にある？」
    """
    try:
        results = _search_campus_db(query, top_k=3)
    except Exception as e:
        return f"キャンパス情報の検索中にエラーが発生しました: {e}"

    if not results:
        return (
            "キャンパス内の該当する施設情報が見つかりませんでした。"
            "別のキーワードで聞いてみてください。"
        )

    # 上位結果を結合して返す
    info_parts = []
    for r in results:
        info_parts.append(r["context"])

    return "\n".join(info_parts)
