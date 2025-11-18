import os
import shutil
import tempfile

import psycopg2
from app.rag.retriever import Retriever
from app.rag.store import RAGStore
from dotenv import load_dotenv
from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

router = APIRouter(prefix="/rag", tags=["RAG"])

load_dotenv()
DB_URL = os.getenv("DB_URL")
store = RAGStore(DB_URL)


@router.post("/upload")
async def upload_csv(file: UploadFile = File(...), source: str = Form(None)):
    """CSVファイルを受け取り、RAGStoreに登録"""
    try:
        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        # === CSV挿入結果を受け取る ===
        result = store.insert_from_csv(tmp_path, source_name=source or file.filename)

        # 例: result = {"inserted": 0, "updated": 7, "skipped": 0}
        inserted = result.get("inserted", 0)
        updated = result.get("updated", 0)
        skipped = result.get("skipped", 0)

        return {
            "status": "success",
            "message": f"{file.filename} processed",
            "insertedCount": inserted,
            "updatedCount": updated,
            "skippedCount": skipped,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/stats")
async def get_stats():
    """登録済みデータの統計情報を返す"""
    try:
        # ✅ ここで新しい接続を毎回開く
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*), COUNT(DISTINCT source) FROM ohsawa_context"
                )
                total, sources = cur.fetchone()

                cur.execute(
                    "SELECT source, COUNT(*) FROM ohsawa_context GROUP BY source"
                )
                data = [{"source": s, "count": c} for s, c in cur.fetchall()]

                # 最終更新日時（最新の updated_at）
                cur.execute("SELECT MAX(updated_at) FROM ohsawa_context")
                last_updated = cur.fetchone()[0]

        return {
            "status": "success",
            "total_records": total,
            "source_count": sources,
            "source_stats": data,
            "last_updated": last_updated.isoformat() if last_updated else None,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/recent")
async def get_recent_updates(limit: int = 10):
    """最近更新されたデータ（最新順）を返す"""
    with store.conn.cursor() as cur:
        cur.execute(
            """
            SELECT context, source, updated_at
            FROM ohsawa_context
            ORDER BY updated_at DESC
            LIMIT %s
        """,
            (limit,),
        )
        rows = cur.fetchall()

    return [
        {
            "context": r[0],
            "source": r[1],
            "updated_at": r[2].isoformat() if r[2] else None,
        }
        for r in rows
    ]


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    threshold: float = 0.25


retriever = Retriever(DB_URL)


@router.post("/query")
async def query_rag(req: QueryRequest):
    """
    RAG 検索テスト用エンドポイント
    """
    try:
        results = retriever.search(
            query=req.query,
            top_k=req.top_k,
            threshold=req.threshold,
        )
        return results

    except Exception as e:
        return {"error": str(e)}
