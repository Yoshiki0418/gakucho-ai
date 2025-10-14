from fastapi import FastAPI

app = FastAPI(title="Gakucho AI Backend", version="0.1.0")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)