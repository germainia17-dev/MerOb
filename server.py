from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from embeddings import Embedder
from sklearn.metrics.pairwise import cosine_similarity
import chromadb
import subprocess
import numpy as np
import sys
import os

# ======================
# CONFIG
# ======================

app = FastAPI(title="Obsidian Chat Memory Server", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://chatgpt.com",
        "https://chat.openai.com",
        "https://claude.ai",
        "https://gemini.google.com",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

model       = None
chroma      = None

# The memory folder is resolved dynamically (env / config.json /
# Obsidian auto-detection) — never hardcoded. See config.py.
import config

VAULT        = config.resolve_vault()
# One .md note per memory, stored in Memories/
MEMORIES_DIR = (VAULT / "Memories") if VAULT else None
VENV_PYTHON  = sys.executable


@app.on_event("startup")
def startup():
    global model, chroma
    model  = Embedder()
    chroma = chromadb.PersistentClient(path="chroma_db")


# ======================
# READING INDIVIDUAL NOTES (Memories/)
# ======================

def read_memory_note(file_path):
    """Extracts the memory text from an individual note.

    Note format:
        > Memory text
        **Category:** [[...]]
        ...
    The memory text is the first line starting with '> '.
    """
    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(">"):
            return line.lstrip("> ").strip()
    return ""


def load_all_memories():
    """Loads all memories from Memories/*.md.
    Returns a list of {file, content}."""
    memories = []
    if not MEMORIES_DIR or not MEMORIES_DIR.exists():
        return memories
    for file in MEMORIES_DIR.glob("*.md"):
        text = read_memory_note(file)
        if text:
            memories.append({"file": file.name, "content": text})
    return memories


# ======================
# ROUTES
# ======================

@app.get("/health")
def health():
    return {"status": "ok", "vault": str(VAULT) if VAULT else None}


RELEVANCE_THRESHOLD = 0.30  # below this → not relevant enough for reinjection


def ranked_results(q: str, n: int):
    """Ranks ALL sources (memories + ChromaDB notes) by true relevance.

    Every source is scored by cosine similarity to the query, then merged
    and sorted globally. No more "score=null" results jumping ahead of the
    genuinely relevant memories.
    """
    query_emb = model.encode([q])
    candidates = []

    # --- 1. Memories (Memories/*.md) — the primary source ---
    memories = load_all_memories()
    if memories:
        texts  = [m["content"] for m in memories]
        embs   = model.encode(texts)
        scores = cosine_similarity(query_emb, embs)[0]
        for m, s in zip(memories, scores):
            candidates.append({
                "source":  "memory",
                "file":    m["file"],
                "content": m["content"],
                "score":   float(s),
            })

    # --- 2. ChromaDB notes (secondary context), scored the same way ---
    try:
        collection = chroma.get_collection("notes")
        data = collection.get(include=["documents"])
        docs = data.get("documents") or []
        ids  = data.get("ids") or []
        if docs:
            embs   = model.encode(docs)
            scores = cosine_similarity(query_emb, embs)[0]
            for doc, _id, s in zip(docs, ids, scores):
                candidates.append({
                    "source":  "notes",
                    "file":    _id,
                    "content": doc,
                    "score":   float(s),
                })
    except Exception:
        pass  # collection empty or missing → continue

    # Global sort by relevance + threshold + top N
    candidates.sort(key=lambda c: c["score"], reverse=True)
    out = []
    for c in candidates:
        if c["score"] < RELEVANCE_THRESHOLD:
            break
        c["score"] = round(c["score"], 3)
        out.append(c)
        if len(out) >= n:
            break
    return out


@app.get("/memories/search")
def search_memories(q: str = Query(..., description="Question or keyword"), n: int = 5):
    """Searches memories + notes, ranked by relevance. Zero API calls."""
    results = ranked_results(q, n)
    return {"query": q, "results": results, "total": len(results)}


@app.get("/memories/context")
def memory_context(q: str = Query(..., description="Topic of the current message"), n: int = 5):
    """Returns a context block ready to inject into a prompt.

    Used for reinjection: the assistant receives the relevant memories
    formatted as text, with no need to rephrase them.
    """
    results = ranked_results(q, n)
    if not results:
        return {"query": q, "context": "", "count": 0}

    lines = ["[Relevant personal memories]"]
    for r in results:
        lines.append(f"- {r['content']}")
    return {"query": q, "context": "\n".join(lines) + "\n", "count": len(results)}


class ExtractRequest(BaseModel):
    conversation: str


@app.post("/extract")
def extract_memories(body: ExtractRequest):
    """
    Receives a conversation as text, writes it to conversation.txt and
    runs memory_extract.py. A single API call (Gemini) happens here.
    """
    if not body.conversation.strip():
        raise HTTPException(status_code=400, detail="Empty conversation.")

    conv_path = Path("conversation.txt")
    conv_path.write_text(body.conversation, encoding="utf-8")

    try:
        result = subprocess.run(
            [VENV_PYTHON, "memory_extract.py"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr)

        return {
            "status":  "ok",
            "message": "Memories extracted and saved to your Obsidian vault.",
            "output":  result.stdout.strip(),
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout: extraction took too long.")


@app.get("/memories/count")
def count_memories():
    """Returns the total number of memories + the breakdown by category."""
    memories = load_all_memories()
    total    = len(memories)

    # Breakdown by category (read from the Categories/ hubs)
    by_category = {}
    categories_dir = (VAULT / "Categories") if VAULT else None
    if categories_dir and categories_dir.exists():
        for hub in categories_dir.glob("*.md"):
            n = sum(1 for l in hub.read_text(encoding="utf-8").splitlines()
                    if l.strip().startswith("- [["))
            by_category[hub.stem] = n

    # Memories pending review
    inbox = Path(".data/inbox/memories_to_review.md")
    pending = 0
    if inbox.exists():
        pending = sum(1 for l in inbox.read_text(encoding="utf-8").splitlines() if l.startswith("- [ ] "))

    return {"total": total, "pending_review": pending, "by_category": by_category}


@app.get("/openapi-gpt.json", include_in_schema=False)
def openapi_gpt():
    """
    Simplified OpenAPI schema for ChatGPT Custom GPT Actions.
    The base URL is injected from the NGROK_URL environment variable.
    """
    base_url = os.getenv("NGROK_URL", "http://localhost:8000")

    schema = {
        "openapi": "3.1.0",
        "info": {
            "title": "Obsidian Chat Memory",
            "version": "1.0",
            "description": "Access to the user's personal memory."
        },
        "servers": [{"url": base_url}],
        "paths": {
            "/memories/search": {
                "get": {
                    "operationId": "searchMemories",
                    "summary": "Search the user's personal memories and notes",
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Question or keyword to search for"
                        },
                        {
                            "name": "n",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 5},
                            "description": "Number of results"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Search results",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        }
                    }
                }
            },
            "/memories/context": {
                "get": {
                    "operationId": "getMemoryContext",
                    "summary": "Relevant memory block ready to inject into the response",
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "User's topic or question"
                        },
                        {
                            "name": "n",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 5},
                            "description": "Number of memories"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Formatted memory context",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        }
                    }
                }
            },
            "/memories/count": {
                "get": {
                    "operationId": "countMemories",
                    "summary": "Number of stored and pending memories",
                    "responses": {
                        "200": {
                            "description": "Memory counters",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        }
                    }
                }
            },
            "/extract": {
                "post": {
                    "operationId": "extractMemories",
                    "summary": "Extract memories from a conversation (1 Gemini call)",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "conversation": {
                                            "type": "string",
                                            "description": "Full text of the conversation"
                                        }
                                    },
                                    "required": ["conversation"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Extraction succeeded",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    return JSONResponse(content=schema)
