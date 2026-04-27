"""
DeepBrief Web API — real-time research briefs with streaming + PDF upload.
"""

import asyncio
import base64
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.engine import DeepBrief, PDFSource, extract_pdf_text, get_llm

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="DeepBrief", version="0.1.0")

# CORS for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF and return extracted text."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return {"error": "Only PDF files are supported"}

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        text = extract_pdf_text(tmp_path)
        return {
            "filename": file.filename,
            "text": text,
            "char_count": len(text),
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)

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

@app.post("/brief-with-pdfs")
async def brief_with_pdfs(
    q: str = Form(...),
    files: list[UploadFile] = File(default=[]),
):
    """Research brief with uploaded PDFs cross-referenced against web sources."""
    if not q or len(q) > 500:
        return StreamingResponse(
            iter([f"event: error\ndata: {{'message': 'Invalid query'}}\n\n"]),
            media_type="text/event-stream",
        )

    pdf_sources: list[PDFSource] = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            continue
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        try:
            text = extract_pdf_text(tmp_path)
            pdf_sources.append(PDFSource(filename=file.filename, text=text))
        finally:
            Path(tmp_path).unlink(missing_ok=True)

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
            async for event in engine.stream_brief(q, pdf_sources):
                yield event
                await asyncio.sleep(0.01)
        except Exception as e:
            yield f"event: error\ndata: {{'message': '{str(e)}'}}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )

@app.post("/brief-page")
async def brief_page(request: Request):
    """Chrome extension endpoint: extract page text and brief it."""
    body = await request.json()
    url = body.get("url", "")
    title = body.get("title", "")
    text = body.get("text", "")[:6000]
    query = body.get("query", f"Summarize and analyze this page: {title}")

    if not text:
        return {"error": "No page text provided"}

    try:
        llm = get_llm()
    except RuntimeError as e:
        return {"error": str(e)}

    from app.engine import LLMClient

    system = """You are DeepBrief. A user has sent you the text of a webpage.
    Write a concise summary with key insights, then answer their specific question.
    Use inline citations [1] if referring to specific claims from the text.
    Format with Markdown headings."""
    user = f"Page: {title}\nURL: {url}\n\nQuestion: {query}\n\nPage text:\n{text}"

    answer = await llm.complete(system, user)
    return {
        "query": query,
        "title": title,
        "url": url,
        "answer": answer,
    }
