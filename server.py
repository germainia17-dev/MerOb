from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import chromadb
import subprocess
import numpy as np
import sys
import os

# ======================
# CONFIG
# ======================

app = FastAPI(title="AI OS Memory Server", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://chat.openai.com",
        "https://claude.ai",
        "https://gemini.google.com",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

model       = None
chroma      = None

# Les mémoires vivent maintenant directement dans le vault Obsidian DigitBrain.
DEFAULT_VAULT = (
    "/Users/MacBook/Library/Mobile Documents/iCloud~md~obsidian/"
    "Documents/DigitBrain/DigitBrain/DIGITBRAIN"
)
memory_dir  = Path(os.getenv("OBSIDIAN_VAULT", DEFAULT_VAULT))
VENV_PYTHON = sys.executable


@app.on_event("startup")
def startup():
    global model, chroma
    model  = SentenceTransformer("all-MiniLM-L6-v2")
    chroma = chromadb.PersistentClient(path="chroma_db")


# ======================
# LECTURE FORMAT TABLEAU
# ======================

def parse_note_rows(file_path):
    """Extrait les mémoires d'une note au format tableau (Date | Mémoire)."""
    rows = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if cells[0].lower() == "date" or set(cells[0]) <= {"-", ":", " "}:
            continue
        rows.append(cells[1])  # le texte de la mémoire
    return rows


# ======================
# ROUTES
# ======================

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/memories/search")
def search_memories(q: str = Query(..., description="Question ou mot-clé"), n: int = 5):
    """
    Cherche dans :
    - ChromaDB (notes vectorisées)
    - AI_OS/Memory/*.md (mémoires validées)
    Retourne les N résultats les plus pertinents. Zéro appel API.
    """

    results = []

    # --- 1. Recherche dans ChromaDB (notes) ---
    try:
        collection    = chroma.get_collection("notes")
        query_emb     = model.encode(q).tolist()
        chroma_result = collection.query(query_embeddings=[query_emb], n_results=min(n, 3))

        for doc, meta_id in zip(chroma_result["documents"][0], chroma_result["ids"][0]):
            results.append({
                "source":  "notes",
                "file":    meta_id,
                "content": doc,
                "score":   None,
            })
    except Exception:
        pass  # collection vide ou absente → on continue

    # --- 2. Recherche vectorielle dans les mémoires validées ---
    memories = []

    for file in memory_dir.rglob("*.md"):
        for text in parse_note_rows(file):
            if text:
                memories.append({"file": file.name, "content": text})

    if memories:
        query_emb    = model.encode([q])
        memory_texts = [m["content"] for m in memories]
        memory_embs  = model.encode(memory_texts)
        scores       = cosine_similarity(query_emb, memory_embs)[0]

        # Top N mémoires par score
        top_indices = np.argsort(scores)[::-1][:n]

        for idx in top_indices:
            if scores[idx] > 0.3:  # seuil minimal de pertinence
                results.append({
                    "source":  "memory",
                    "file":    memories[idx]["file"],
                    "content": memories[idx]["content"],
                    "score":   round(float(scores[idx]), 3),
                })

    if not results:
        return {"query": q, "results": [], "total": 0}

    return {"query": q, "results": results, "total": len(results)}


class ExtractRequest(BaseModel):
    conversation: str


@app.post("/extract")
def extract_memories(body: ExtractRequest):
    """
    Reçoit une conversation en texte, l'écrit dans conversation.txt
    et lance memory_extract.py. Un seul appel API (Gemini) se produit ici.
    """
    if not body.conversation.strip():
        raise HTTPException(status_code=400, detail="Conversation vide.")

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
            "message": "Mémoires extraites → AI_OS/Inbox/memories_to_review.md",
            "output":  result.stdout.strip(),
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout : extraction trop longue.")


@app.get("/memories/count")
def count_memories():
    """Retourne le nombre de mémoires par fichier + le total à valider."""
    counts = {}
    total  = 0

    for file in memory_dir.rglob("*.md"):
        n = len(parse_note_rows(file))
        if n:
            counts[file.name] = n
            total += n

    # Mémoires en attente de validation
    inbox = Path("AI_OS/Inbox/memories_to_review.md")
    pending = 0

    if inbox.exists():
        pending = sum(1 for l in inbox.read_text(encoding="utf-8").splitlines() if l.startswith("- [ ] "))

    return {"total": total, "pending_review": pending, "by_file": counts}


@app.get("/openapi-gpt.json", include_in_schema=False)
def openapi_gpt():
    """
    Schéma OpenAPI simplifié pour ChatGPT Custom GPT Actions.
    L'URL de base est injectée depuis la variable d'env NGROK_URL.
    """
    base_url = os.getenv("NGROK_URL", "http://localhost:8000")

    schema = {
        "openapi": "3.1.0",
        "info": {
            "title": "AI OS Memory",
            "version": "1.0",
            "description": "Accès à la mémoire personnelle de l'utilisateur."
        },
        "servers": [{"url": base_url}],
        "paths": {
            "/memories/search": {
                "get": {
                    "operationId": "searchMemories",
                    "summary": "Cherche dans les mémoires et notes personnelles",
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Question ou mot-clé à rechercher"
                        },
                        {
                            "name": "n",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 5},
                            "description": "Nombre de résultats"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Résultats de la recherche",
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
                    "summary": "Nombre de mémoires stockées et en attente",
                    "responses": {
                        "200": {
                            "description": "Compteurs de mémoires",
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
                    "summary": "Extrait les mémoires d'une conversation (1 appel Gemini)",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "conversation": {
                                            "type": "string",
                                            "description": "Texte complet de la conversation"
                                        }
                                    },
                                    "required": ["conversation"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Extraction réussie",
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
