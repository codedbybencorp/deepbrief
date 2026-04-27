"""
CLI usage for DeepBrief.

Usage:
    python -m app.cli "latest quantum computing developments"
"""

import asyncio
import json
import sys

from app.engine import DeepBrief, get_llm


async def main():
    try:
        llm = get_llm()
    except RuntimeError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Research query: ")
    if not query:
        print("No query provided")
        sys.exit(1)

    engine = DeepBrief(llm)
    print(f"🔍 Researching: {query}\n")

    async for event in engine.stream_brief(query):
        line = event.strip()
        if line.startswith("event:"):
            parts = line.split("\n")
            evt = parts[0].replace("event: ", "").strip()
            data = ""
            for p in parts:
                if p.startswith("data: "):
                    data = p.replace("data: ", "")
                    break
            if evt == "status":
                d = json.loads(data)
                print(f"  {d.get('message', '')}")
            elif evt == "sources":
                d = json.loads(data)
                print(f"  Found {d['count']} sources")
            elif evt == "done":
                d = json.loads(data)
                print(f"\n{'='*60}")
                print("DEEP BRIEF")
                print(f"{'='*60}\n")
                print(d["answer"])
                print(f"\n{'='*60}")
                srcs = d.get('sources', [])
                print(f"Sources: {len(srcs)} | Search: {d.get('search_time')}s | Read: {d.get('read_time')}s")


if __name__ == "__main__":
    asyncio.run(main())
