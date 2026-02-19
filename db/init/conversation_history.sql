-- === 対話履歴テーブル ===
CREATE TABLE IF NOT EXISTS conversation_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,       -- 'user' or 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- === 検索用インデックス（user_id + session_id + 時系列降順） ===
CREATE INDEX IF NOT EXISTS idx_conv_hist_session
ON conversation_history (user_id, session_id, created_at DESC);
