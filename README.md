# DeepBrief — Research Intelligence

> **Ask anything. Get a cited research brief in seconds.**

**[🌐 Landing Page](https://github.com/codedbybencorp/deepbrief-landing)** | **[📦 Main Repo](https://github.com/codedbybencorp/deepbrief)**

DeepBrief searches the web, reads sources, and synthesizes comprehensive answers with inline citations. No more opening 20 tabs to understand a topic.

![demo](https://img.shields.io/badge/demo-live-brightgreen)

---

## What it does

1. **Searches the web** — Uses DuckDuckGo to find the most relevant sources
2. **Reads sources** — Extracts clean text from the top results
3. **Synthesizes** — Uses an LLM (OpenAI, Ollama, or OpenRouter) to write a cited brief
4. **Streams in real-time** — Watch it work: search → read → synthesize → done

## Demo

```
🔍 Researching: benefits of mediterranean diet

  Searching the web for: benefits of mediterranean diet
  Found 8 sources
  Reading 4 sources...
  Synthesizing answer with citations...

============================================================
DEEP BRIEF
============================================================

# DeepBrief Research Report: Benefits of the Mediterranean Diet

The Mediterranean diet is an eating pattern inspired by the traditional
culinary habits of people living in countries bordering the Mediterranean
Sea [2], [4]...

Sources: 4 | Search: 2.18s | Read: 2.4s
```

## Quick Start

### Option 1: With Ollama (fully local, free)

```bash
# 1. Install Ollama and pull a model
ollama run gemma-4-e4b

# 2. Clone and run
git clone https://github.com/codedbybencorp/deepbrief.git
cd deepbrief
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8090

# 3. Open http://localhost:8090
```

### Option 2: With OpenAI

```bash
export OPENAI_API_KEY=sk-...
uvicorn app.main:app --reload --port 8090
```

### Option 3: Docker

```bash
docker compose up -d
# Open http://localhost:8090
```

## CLI Usage

```bash
python -m app.cli "latest quantum computing developments"
```

## LLM Backends

| Provider | How to enable | Notes |
|----------|--------------|-------|
| **OpenAI** | `export OPENAI_API_KEY=sk-...` | Fast, high quality |
| **Ollama** | `ollama run gemma-4-e4b` | Fully local, free |
| **OpenRouter** | Coming soon | Access many models |

Auto-detection priority: OpenAI → Ollama → error.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   User      │────▶│   FastAPI    │────▶│  DuckDuckGo │
│  Query      │     │   SSE Stream │     │   Search    │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   DeepBrief  │
                    │   Engine     │
                    └──────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌─────────┐  ┌─────────┐
        │  Read   │  │ Synthe- │  │  LLM    │
        │ Sources │  │  size   │  │ (Ollama │
        │ (BS4)   │  │         │  │ /OpenAI)│
        └─────────┘  └─────────┘  └─────────┘
```

## Tech Stack

- **Python 3.12** + FastAPI
- **DuckDuckGo** HTML search (no API key)
- **BeautifulSoup** + lxml for content extraction
- **SSE streaming** for real-time UX
- **Ollama / OpenAI** for synthesis
- **Docker** + docker-compose for deployment

## Why this exists

Information overload is real. When you want to understand a topic, you open tab after tab, skim articles, and still don't know what the consensus is. DeepBrief does the legwork: it finds sources, reads them, and tells you what they actually say — with citations so you can verify.

## License

MIT

---

## What's Next

- [ ] **Deploy backend to Fly.io** — Current priority. The landing page iframe demo only works locally. Deploying to Fly.io will make the live demo work for all visitors.
- [ ] Add Stripe billing for hosted version
- [ ] Chrome Web Store submission for extension
- [ ] Add OpenRouter support for more LLM backends

---

Built with Claude Code + DuckDuckGo + Ollama
