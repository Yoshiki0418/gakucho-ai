FROM postgres:14

# pgvector拡張を追加
RUN apt-get update && apt-get install -y postgresql-14-pgvector && rm -rf /var/lib/apt/lists/*

# 初期スキーマを適用
COPY ./init/schema.sql /docker-entrypoint-initdb.d/01_schema.sql
COPY ./init/conversation_history.sql /docker-entrypoint-initdb.d/02_conversation_history.sql
