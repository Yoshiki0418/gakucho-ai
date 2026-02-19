import os

from app.routers import audio_stream_router, rag_router, text_chat_router
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Explicitly load from the mounted path (Docker DevContainer)
env_path = "/workspace/backend/.env"
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()  # Fallback

# =========================================================
# アプリ初期化
# =========================================================
app = FastAPI(
    title="Gakucho AI Backend",
    version="0.1.0",
    description=(
        "金沢工業大学 学長AIプロジェクトのバックエンドAPIです。\n\n"
        "- `/api/text-chat/stream` : テキスト入力を受け取りストリーミングで返答（文章単位）\n"
        "- `/api/text-chat/char-stream` : テキスト入力を受け取りストリーミング返答（単語単位）\n"
        "- `/ws/audio-stream` : 音声入力をリアルタイムで処理"
    ),
    contact={
        "name": "Gakucho AI Project Team",
        "email": "c1206618@st.kanazawa-it.ac.jp",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# =========================================================
# CORS設定
# =========================================================
origins = [
    "http://localhost:4000",
    "localhost:4000/",
    "http://127.0.0.1:4000",
    "http://192.168.29.16:4000",
    "http://localhost:4001",
    "http://127.0.0.1:4001",
    "http://192.168.29.16:4001",
    "http://192.168.29.16:30212",
    "https://192.168.29.16",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# ルーター登録
# =========================================================
app.include_router(text_chat_router.router)
app.include_router(audio_stream_router.router)
app.include_router(rag_router.router)


# =========================================================
# ヘルスチェック
# =========================================================


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# =========================================================
# 起動設定
# =========================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8076, reload=True)
