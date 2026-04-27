"""
DeepBrief Web API — real-time research briefs with streaming.
"""

import asyncio
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.engine import DeepBrief, get_llm

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="DeepBrief", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}

@app.get("/brief")
async def brief_stream(q: str):
    if not q or len(q) > 500:
        return StreamingResponse(
            iter([f"event: error\ndata: {{'message': 'Invalid query'}}\n\n"]),
            media_type="text/event-stream",
        )

    try:
        llm = get_llm()
    except RuntimeError as e:
        return StreamingResponse(
            iter([f"event: error\ndata: {{'message': '{str(e)}'}}\n\n"]),
            media_type="text/event-stream",
        )

    engine = DeepBrief(llm)

    async def gen():
        try:
            async for event in engine.stream_brief(q):
                yield event
                await asyncio.sleep(0.01)
        except Exception as e:
            yield f"event: error\ndata: {{'message': '{str(e)}'}}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
