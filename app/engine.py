"""
DeepBrief — Research intelligence engine.
Search the web, read sources, synthesize answers with citations.
Supports PDF upload for cross-referencing.
"""

import asyncio
import json
import os
import re
import textwrap
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


# ── LLM providers ──────────────────────────────────────────────────

class LLMClient:
    async def complete(self, system: str, user: str) -> str:
        raise NotImplementedError


class OllamaClient(LLMClient):
    def __init__(self, model: str = "gemma-4-e4b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.url = f"{base_url}/api/generate"

    async def complete(self, system: str, user: str) -> str:
        prompt = f"{system}\n\n{user}"
        async with httpx.AsyncClient(timeout=120) as http:
            r = await http.post(self.url, json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_ctx": 8192},
            })
            r.raise_for_status()
            return r.json().get("response", "")


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def complete(self, system: str, user: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=4000,
        )
        return response.choices[0].message.content or ""


def get_llm() -> LLMClient:
    if key := os.environ.get("OPENAI_API_KEY"):
        try:
            return OpenAIClient(key)
        except Exception:
            pass
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        return OllamaClient()
    except Exception:
        pass
    raise RuntimeError("No LLM available. Set OPENAI_API_KEY or start Ollama.")


# ── Data models ────────────────────────────────────────────────────

@dataclass
class Source:
    url: str
    title: str
    snippet: str
    text: str = ""
    domain: str = ""

    def __post_init__(self):
        self.domain = urlparse(self.url).netloc.replace("www.", "")


@dataclass
class PDFSource:
    filename: str
    text: str


@dataclass
class BriefResult:
    query: str
    answer: str
    sources: list[Source]
    pdf_sources: list[PDFSource]
    search_time: float
    read_time: float
    generated_at: str


# ── PDF parsing ────────────────────────────────────────────────────

def extract_pdf_text(path: str | Path) -> str:
    import fitz  # pymupdf
    doc = fitz.open(str(path))
    chunks = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            chunks.append(text.strip())
    doc.close()
    full = "\n\n".join(chunks)
    # Truncate to ~8000 chars to save context
    return full[:8000]


# ── Engine ─────────────────────────────────────────────────────────

class DeepBrief:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or get_llm()

    # ── Search ─────────────────────────────────────────────────────
    async def _search(self, query: str, limit: int = 8) -> list[Source]:
        if os.environ.get("TAVILY_API_KEY"):
            return await self._search_tavily(query, limit)
        return await self._search_ddg(query, limit)

    async def _search_tavily(self, query: str, limit: int = 8) -> list[Source]:
        from tavily import AsyncTavilyClient
        client = AsyncTavilyClient()
        response = await client.search(query=query, max_results=limit)
        results = []
        for r in response.get("results", []):
            results.append(Source(
                url=r.get("url", ""),
                title=r.get("title", ""),
                snippet=r.get("content", ""),
            ))
        return results

    async def _search_ddg(self, query: str, limit: int = 8) -> list[Source]:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as http:
            r = await http.post(url, data={"q": query, "kl": "us-en"}, headers=headers)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

        results = []
        for res in soup.select(".result"):
            a = res.select_one(".result__a")
            snippet_el = res.select_one(".result__snippet")
            if not a:
                continue
            href = a.get("href", "")
            if href.startswith("/"):
                continue
            title = a.get_text(strip=True)
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            results.append(Source(url=href, title=title, snippet=snippet))
            if len(results) >= limit:
                break
        return results

    # ── Read ───────────────────────────────────────────────────────
    async def _read(self, source: Source) -> Source:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as http:
                r = await http.get(source.url, headers=headers)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    tag.decompose()
                main = soup.find("article") or soup.find("main") or soup.find("body")
                text = main.get_text(separator="\n", strip=True) if main else ""
                text = re.sub(r"\n{3,}", "\n\n", text)
                text = re.sub(r" +", " ", text)
                source.text = text[:4000]
        except Exception:
            source.text = source.snippet
        return source

    # ── Synthesize ─────────────────────────────────────────────────
    async def _synthesize(self, query: str, sources: list[Source], pdf_sources: list[PDFSource]) -> str:
        context_parts = []
        for i, s in enumerate(sources, 1):
            context_parts.append(
                f"[Web Source {i}] {s.title}\nURL: {s.domain}\n{s.text[:3000]}"
            )
        for i, p in enumerate(pdf_sources, 1):
            context_parts.append(
                f"[PDF Source {i}] {p.filename}\n{p.text[:3000]}"
            )
        context = "\n\n---\n\n".join(context_parts)

        system = textwrap.dedent("""\
            You are DeepBrief, a research intelligence engine.
            Read the provided web and PDF sources and write a comprehensive, fact-checked answer.

            Rules:
            1. Every factual claim must cite its source using [W1], [W2] for web sources and [P1], [P2] for PDF sources.
            2. If sources conflict, present multiple viewpoints clearly.
            3. If information is missing, say so explicitly.
            4. Write in clear, professional prose. Use headings and bullet points.
            5. End with a "Sources" section listing each citation number, title, and domain/filename.
            6. Do NOT make up facts not present in the sources.
            7. When PDF sources are provided, cross-reference them with web sources and highlight agreements or contradictions.
        """)
        user = f"Question: {query}\n\nSources:\n{context}"
        return await self.llm.complete(system, user)

    # ── Stream ─────────────────────────────────────────────────────
    async def stream_brief(
        self, query: str, pdf_sources: list[PDFSource] | None = None
    ) -> AsyncIterator[str]:
        import time
        t0 = time.time()
        pdf_sources = pdf_sources or []

        yield _sse("status", {"step": "search", "message": f"Searching the web for: {query}"})
        sources = await self._search(query)
        yield _sse("sources", {"count": len(sources), "urls": [s.url for s in sources]})
        search_time = time.time() - t0

        yield _sse("status", {"step": "read", "message": f"Reading {min(4, len(sources))} web sources..."})
        read_tasks = [self._read(s) for s in sources[:4]]
        read_sources = await asyncio.gather(*read_tasks)
        read_time = time.time() - t0 - search_time

        if pdf_sources:
            yield _sse("status", {"step": "pdf", "message": f"Analyzing {len(pdf_sources)} PDF document(s)..."})

        yield _sse("status", {"step": "synthesize", "message": "Synthesizing answer with citations..."})
        answer = await self._synthesize(query, list(read_sources), pdf_sources)

        result = BriefResult(
            query=query,
            answer=answer,
            sources=list(read_sources),
            pdf_sources=pdf_sources,
            search_time=round(search_time, 2),
            read_time=round(read_time, 2),
            generated_at=datetime.utcnow().isoformat() + "Z",
        )
        yield _sse("done", asdict(result))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
