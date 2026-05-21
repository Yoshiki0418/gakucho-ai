import os

import pandas as pd
import psycopg2
import torch
import torch.nn.functional as F
from psycopg2 import Error as PsycopgError
from sentence_transformers import SentenceTransformer


class RAGStore:
    """RAGデータをPostgreSQL + pgvectorに格納・検索するためのStoreクラス"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = psycopg2.connect(db_url)
        self.conn.autocommit = True
        self.model = SentenceTransformer("cl-nagoya/ruri-v3-310m")
        # 環境変数 RAG_EMBED_DEVICE で device を強制できる（"cpu" / "cuda"）。
        # GPU で NaN が出るケースを避けたいときは "cpu" を指定する。
        forced = os.environ.get("RAG_EMBED_DEVICE")
        if forced:
            self.device = forced
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

    # ==========================================================
    # 内部ユーティリティ: CSV の自動エンコーディング読み込み
    # ==========================================================
    def _read_csv_auto_encoding(self, csv_path: str) -> pd.DataFrame:
        """
        CSV を複数のエンコーディングで試し読みし、
        うまくいったものを返す。ダメなら chardet で推定。
        """
        tried_encodings: list[str] = []

        # よく使う日本語系 + UTF 系を優先して試す
        candidate_encodings = [
            "utf-8",
            "utf-8-sig",
            "cp932",  # Windows 日本語
            "shift_jis",
            "euc-jp",
        ]

        for enc in candidate_encodings:
            try:
                df = pd.read_csv(csv_path, dtype=str, encoding=enc)
                print(f"📄 CSV encoding detected as '{enc}' (trial)")
                return df
            except UnicodeDecodeError:
                tried_encodings.append(enc)
                continue

        try:
            import chardet

            with open(csv_path, "rb") as f:
                raw = f.read(200_000)  # 最初の 200KB だけを見る
            detected = chardet.detect(raw)
            enc = detected.get("encoding")
            if enc:
                try:
                    df = pd.read_csv(csv_path, dtype=str, encoding=enc)
                    print(f"📄 CSV encoding auto-detected by chardet as '{enc}'")
                    return df
                except UnicodeDecodeError:
                    tried_encodings.append(enc)
        except ImportError:
            pass

        # ここまで来たら全部失敗
        raise UnicodeDecodeError(
            "csv",
            b"",
            0,
            0,
            f"CSV の読み込みに失敗しました。試した encoding: {tried_encodings}。",
        )

    def insert_from_csv(self, csv_path: str, source_name: str | None = None):
        """CSVを読み込み、context列をembeddingしてDBに格納（重複は更新 or スキップ）"""
        inserted = 0
        updated = 0
        skipped = 0
        skipped_index_limit = 0  # index row too large で飛ばした件数

        df = self._read_csv_auto_encoding(csv_path).fillna("")

        if "context" not in df.columns:
            raise ValueError(
                f"'context' 列が CSV '{csv_path}' に存在しません。列名を確認してください。"
            )

        contexts = df["context"].tolist()

        # source_url列がない場合は空文字を補完
        if "source_url" in df.columns:
            source_urls = df["source_url"].tolist()
        else:
            source_urls = [""] * len(df)

        docs = [f"検索文書: {c}" for c in contexts]
        embeddings = self.model.encode(docs, convert_to_tensor=True, device=self.device)
        embeddings = F.normalize(embeddings, p=2, dim=1)

        # NaN/Inf を含む embedding が出た場合は pgvector に拒否されるため弾く
        nan_mask = torch.isnan(embeddings).any(dim=1) | torch.isinf(embeddings).any(dim=1)
        n_nan = int(nan_mask.sum().item())
        if n_nan > 0:
            print(f"⚠️ {n_nan} 件の embedding に NaN/Inf が含まれていたためスキップします。")

        # ★ autocommit=True 前提なので connection の with はやめる
        with self.conn.cursor() as cur:
            for idx, (context, emb, source_url) in enumerate(zip(contexts, embeddings, source_urls)):
                if nan_mask[idx].item():
                    skipped += 1
                    continue
                emb_list = emb.cpu().tolist()
                source = source_name or os.path.basename(csv_path)

                try:
                    # --- まずINSERT試行 ---
                    cur.execute(
                        """
                        INSERT INTO ohsawa_context (context, embedding, source, source_url, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (context, source) DO NOTHING
                        """,
                        (context, emb_list, source, source_url),
                    )

                    if cur.rowcount > 0:
                        inserted += 1
                        continue  # 次のレコードへ

                    # --- 重複していた場合は手動でUPDATE ---
                    cur.execute(
                        """
                        UPDATE ohsawa_context
                        SET embedding = %s, source_url = %s, updated_at = NOW()
                        WHERE context = %s AND source = %s
                        """,
                        (emb_list, source_url, context, source),
                    )

                    if cur.rowcount > 0:
                        updated += 1
                    else:
                        # ここは「重複していたが内容は同じで何も変わらなかった」など
                        skipped += 1

                except PsycopgError as e:
                    msg = str(e)
                    pgcode = getattr(e, "pgcode", None)

                    # index row requires XXXX bytes, maximum size is 8191
                    if "maximum size is 8191" in msg or pgcode == "54000":
                        skipped += 1
                        skipped_index_limit += 1

                        # autocommit=True なので rollback は不要＆しない
                        preview = context.replace("\n", " ")[:120]
                        print(
                            "⚠️ Skipped row due to index row size limit "
                            f"(len(context)={len(context)}): {preview!r}"
                        )
                        continue

                    # それ以外のDBエラーはそのまま上に投げる
                    raise

        print(f"✅ Upserted {inserted} records from {csv_path}")
        if updated > 0:
            print(f"🔄 Updated {updated} existing records.")
        if skipped > 0:
            print(f"⚠️ Skipped {skipped} records (no changes or errors).")
        if skipped_index_limit > 0:
            print(
                f"🧱 Skipped {skipped_index_limit} records due to "
                "PostgreSQL index row size limit (8191 bytes)."
            )

        return {
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "skipped_index_limit": skipped_index_limit,
        }

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
