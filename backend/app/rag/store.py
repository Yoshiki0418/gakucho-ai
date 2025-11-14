import os
from datetime import datetime

import pandas as pd
import psycopg2
import torch
import torch.nn.functional as F
from sentence_transformers import SentenceTransformer


class RAGStore:
    """RAGデータをPostgreSQL + pgvectorに格納・検索するためのStoreクラス"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = psycopg2.connect(db_url)
        self.conn.autocommit = True
        self.model = SentenceTransformer("cl-nagoya/ruri-v3-310m")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    # ==========================================================
    # 挿入処理
    # ==========================================================
    def insert_from_csv(self, csv_path: str, source_name: str | None = None):
        """CSVを読み込み、context列をembeddingしてDBに格納（重複は更新 or スキップ）"""
        inserted = 0
        updated = 0
        skipped = 0

        df = pd.read_csv(csv_path, dtype=str).fillna("")
        contexts = df["context"].tolist()

        docs = [f"検索文書: {c}" for c in contexts]
        embeddings = self.model.encode(docs, convert_to_tensor=True, device=self.device)
        embeddings = F.normalize(embeddings, p=2, dim=1)

        inserted, updated, skipped = 0, 0, 0
        with self.conn, self.conn.cursor() as cur:
            for context, emb in zip(contexts, embeddings):
                emb_list = emb.cpu().tolist()
                source = source_name or os.path.basename(csv_path)

                # --- まずINSERT試行 ---
                cur.execute(
                    """
                    INSERT INTO ohsawa_context (context, embedding, source, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                    """,
                    (context, emb_list, source),
                )

                if cur.rowcount > 0:
                    inserted += 1
                else:
                    # --- 重複していた場合は手動でUPDATE ---
                    cur.execute(
                        """
                        UPDATE ohsawa_context
                        SET embedding = %s, updated_at = NOW()
                        WHERE context = %s AND source = %s
                        """,
                        (emb_list, context, source),
                    )
                    if cur.rowcount > 0:
                        updated += 1
                    else:
                        skipped += 1

        print(f"✅ Upserted {inserted} records from {csv_path}")
        if updated > 0:
            print(f"🔄 Updated {updated} existing records.")
        if skipped > 0:
            print(f"⚠️ Skipped {skipped} records (no changes).")

        return {
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
        }

    # ==========================================================
    # 検索処理
    # ==========================================================
    def search(self, query: str, top_k: int = 5):
        """PostgreSQL内でコサイン類似度検索"""
        query_text = f"検索クエリ: {query}"
        query_emb = self.model.encode(
            [query_text], convert_to_tensor=True, device=self.device
        )
        query_emb = F.normalize(query_emb, p=2, dim=1).cpu().tolist()[0]

        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, context, 1 - (embedding <=> %s::vector) AS similarity
                FROM ohsawa_context
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_emb, query_emb, top_k),
            )
            results = cur.fetchall()

        return [
            {"id": r[0], "context": r[1], "similarity": float(r[2])} for r in results
        ]

    # ==========================================================
    # ベクター検索処理
    # ==========================================================
    def search_by_vector(self, query_emb, top_k=5):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, context, 1 - (embedding <=> %s::vector) AS similarity "
                "FROM ohsawa_context "
                "ORDER BY embedding <=> %s::vector LIMIT %s",
                (query_emb, query_emb, top_k),
            )
            return cur.fetchall()

    # ==========================================================
    # ユーティリティ
    # ==========================================================
    def close(self):
        self.conn.close()
