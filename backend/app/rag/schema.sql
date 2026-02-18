-- === pgvector拡張の有効化 ===
CREATE EXTENSION IF NOT EXISTS vector;

-- === 学長AI用RAGストアテーブル ===
CREATE TABLE IF NOT EXISTS ohsawa_context (
    id SERIAL PRIMARY KEY,
    context TEXT,
    embedding VECTOR(768),   -- SentenceTransformer出力
    source TEXT,             -- CSV元ファイル名など
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (context, source)  -- context＋sourceの組み合わせで一意制約
);

-- === embedding列に対する近傍検索インデックス ===
-- HNSWは高速かつ精度高いANN検索
CREATE INDEX IF NOT EXISTS idx_ohsawa_context_embedding
ON ohsawa_context
USING hnsw (embedding vector_cosine_ops);
