from app.routers import text_chat_router
from fastapi import FastAPI

app = FastAPI(title="Gakucho AI Backend", version="0.1.0")

# ===== ルーター登録 =====
app.include_router(text_chat_router.router)


# ===== ヘルスチェック =====
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ===== 起動設定 =====
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
