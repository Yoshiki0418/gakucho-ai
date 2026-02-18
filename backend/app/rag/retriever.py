from typing import Any, Optional

import psycopg2
import torch
import torch.nn.functional as F
from sentence_transformers import SentenceTransformer


# ======================================================
# Retriever クラス
# ======================================================
class Retriever:
    """
    RAGStore に保存された学内情報データから、
    クエリに応じて関連情報を高精度に検索するためのクラス。

    - ベクトル検索（pgvector）
    - 閾値フィルタ
    - メタデータ検索（将来拡張用）
    """

    def __init__(
        self,
        db_url: str,
        embedding_model: str = "cl-nagoya/ruri-v3-310m",
    ):
        self.conn = psycopg2.connect(db_url)
        self.conn.autocommit = True

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(embedding_model)

    # ======================================================
    # 埋め込み生成
    # ======================================================
    def embed(self, text: str) -> list[float]:
        """テキストを正規化済みベクトルへ変換"""
        emb = self.model.encode([text], convert_to_tensor=True, device=self.device)
        emb = F.normalize(emb, p=2, dim=1)
        return emb[0].cpu().tolist()

    # ======================================================
    # メイン検索処理
    # ======================================================
    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.25,
        metadata_filter: Optional[dict[str, str]] = None,
    ) -> list[dict[str, Any]]:
        """
        pgvector による埋め込み検索。
        metadata_filter は {"category": "奨学金"} のような形式で使用可能（今後拡張用）
        """
        emb = self.embed(f"検索クエリ: {query}")

        # SQL の WHERE を動的に構築
        where_sql = ""
        params: list[Any] = [emb, emb, top_k]

        if metadata_filter:
            conditions = []
            for key, value in metadata_filter.items():
                conditions.append("metadata->>%s = %s")
                params.insert(1, key)
                params.insert(2, value)
            where_sql = "WHERE " + " AND ".join(conditions)

        sql = f"""
            SELECT id, context, source,
                   1 - (embedding <=> %s::vector) AS sim
            FROM ohsawa_context
            {where_sql}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """

        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        # 閾値で低スコアを除外
        results = [
            {
                "id": r[0],
                "context": r[1],
                "source": r[2],
                "similarity": float(r[3]),
            }
            for r in rows
            if float(r[3]) >= threshold
        ]

        return results

    # ======================================================
    # 将来の hybrid-search への拡張（placeholder）
    # ======================================================
    def hybrid_search(self, query: str, top_k: int = 5):
        """
        BM25（keyword）＋ pgvector（semantic）を組み合わせるための器。
        学長AI用に後日実装可能（例：学則のキーワード検索）
        """
        pass

    # ======================================================
    # 終了処理
    # ======================================================
    def close(self):
        self.conn.close()
