from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import os
from app.engine import DeepBrief

app = FastAPI(title="DeepBrief", version="0.1.0")

# Static files — serve index.html directly
templates = Jinja2Templates(directory="static")
app.mount("/static", StaticFiles(directory="static"), name="static")

OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
TAVILY_KEY = os.environ.get("TAVILY_API_KEY")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/brief")
async def brief_stream(q: str):
    if not q or len(q) > 500:
        return StreamingResponse(
            iter([f"event: error\ndata: {{'message': 'Invalid query'}}\n\n"]),
            media_type="text/event-stream",
        )
    if not OPENAI_KEY:
        return StreamingResponse(
            iter([f"event: error\ndata: {{'message': 'OPENAI_API_KEY not set'}}\n\n"]),
            media_type="text/event-stream",
        )

    engine = DeepBrief(OPENAI_KEY)

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
