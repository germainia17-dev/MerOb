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
VAULT        = Path(os.getenv("OBSIDIAN_VAULT", DEFAULT_VAULT))
# Depuis la Phase A : une note .md par mémoire dans Memories/
MEMORIES_DIR = VAULT / "Memories"
VENV_PYTHON  = sys.executable


@app.on_event("startup")
def startup():
    global model, chroma
    model  = SentenceTransformer("all-MiniLM-L6-v2")
    chroma = chromadb.PersistentClient(path="chroma_db")


# ======================
# LECTURE DES NOTES INDIVIDUELLES (Memories/)
# ======================

def read_memory_note(file_path):
    """Extrait le texte d'une mémoire depuis une note individuelle.

    Format de note (Phase A) :
        > Texte de la mémoire
        **Catégorie :** [[...]]
        ...
    Le texte de la mémoire est la première ligne commençant par '> '.
    """
    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(">"):
            return line.lstrip("> ").strip()
    return ""


def load_all_memories():
    """Charge toutes les mémoires depuis Memories/*.md.
    Retourne une liste de {file, content}."""
    memories = []
    if not MEMORIES_DIR.exists():
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
    return {"status": "ok"}


RELEVANCE_THRESHOLD = 0.30  # en-dessous → pas assez pertinent pour la réinjection


def ranked_results(q: str, n: int):
    """Classe TOUTES les sources (mémoires + notes ChromaDB) par pertinence réelle.

    Toutes les sources sont scorées par similarité cosinus avec la requête,
    puis fusionnées et triées globalement. Plus de résultats "score=null"
    qui passaient devant les vraies mémoires pertinentes.
    """
    query_emb = model.encode([q])
    candidates = []

    # --- 1. Mémoires (Memories/*.md) — la source principale ---
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

    # --- 2. Notes ChromaDB (contexte secondaire), scorées de la même façon ---
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
        pass  # collection vide ou absente → on continue

    # Tri global par pertinence + seuil + top N
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
def search_memories(q: str = Query(..., description="Question ou mot-clé"), n: int = 5):
    """Cherche dans les mémoires + notes, triées par pertinence. Zéro appel API."""
    results = ranked_results(q, n)
    return {"query": q, "results": results, "total": len(results)}


@app.get("/memories/context")
def memory_context(q: str = Query(..., description="Sujet du message en cours"), n: int = 5):
    """Renvoie un bloc de contexte prêt à injecter dans un prompt.

    Utilisé pour la réinjection : l'IA reçoit les mémoires pertinentes
    formatées en texte, sans avoir à les reformuler.
    """
    results = ranked_results(q, n)
    if not results:
        return {"query": q, "context": "", "count": 0}

    lines = ["[Mémoires personnelles pertinentes]"]
    for r in results:
        lines.append(f"- {r['content']}")
    return {"query": q, "context": "\n".join(lines) + "\n", "count": len(results)}


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
    """Retourne le nombre total de mémoires + la répartition par catégorie."""
    memories = load_all_memories()
    total    = len(memories)

    # Répartition par catégorie (lue depuis les hubs Categories/)
    by_category = {}
    categories_dir = VAULT / "Categories"
    if categories_dir.exists():
        for hub in categories_dir.glob("*.md"):
            n = sum(1 for l in hub.read_text(encoding="utf-8").splitlines()
                    if l.strip().startswith("- [["))
            by_category[hub.stem] = n

    # Mémoires en attente de validation
    inbox = Path("AI_OS/Inbox/memories_to_review.md")
    pending = 0
    if inbox.exists():
        pending = sum(1 for l in inbox.read_text(encoding="utf-8").splitlines() if l.startswith("- [ ] "))

    return {"total": total, "pending_review": pending, "by_category": by_category}


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
            "/memories/context": {
                "get": {
                    "operationId": "getMemoryContext",
                    "summary": "Bloc de mémoires pertinentes prêt à injecter dans la réponse",
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Sujet ou question de l'utilisateur"
                        },
                        {
                            "name": "n",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 5},
                            "description": "Nombre de mémoires"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Contexte mémoire formaté",
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
