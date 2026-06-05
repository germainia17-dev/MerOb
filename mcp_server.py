from mcp.server.fastmcp import FastMCP
from pathlib import Path
from embeddings import Embedder
from sklearn.metrics.pairwise import cosine_similarity
import chromadb
import subprocess
import numpy as np
import sys

import config

# ======================
# CONFIG
# ======================

mcp         = FastMCP("Obsidian Chat Memory")
model       = Embedder()
chroma      = chromadb.PersistentClient(path=str(Path(__file__).parent / "chroma_db"))

# Memories live as one .md note per memory in <vault>/Memories/ — resolved
# dynamically (env / config.json / Obsidian auto-detection). See config.py.
VAULT       = config.resolve_vault()
MEMORIES_DIR = (VAULT / "Memories") if VAULT else None
VENV_PYTHON = sys.executable


def read_memory_note(file_path) -> str:
    """Returns the memory text (first line starting with '> ') of a note."""
    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(">"):
            return line.lstrip("> ").strip()
    return ""


def load_all_memories() -> list:
    """Loads every memory from <vault>/Memories/*.md."""
    memories = []
    if not MEMORIES_DIR or not MEMORIES_DIR.exists():
        return memories
    for file in MEMORIES_DIR.rglob("*.md"):
        text = read_memory_note(file)
        if text:
            memories.append({"file": file.name, "content": text})
    return memories


# ======================
# MCP TOOLS
# ======================

@mcp.tool()
def search_memories(query: str, n: int = 5) -> str:
    """
    Search the user's personal notes and memories.
    Uses local vector search — no API call.
    Call this at the start of a conversation to personalize the context.
    """
    results = []

    # --- ChromaDB (indexed notes) ---
    try:
        collection = chroma.get_collection("notes")
        query_emb  = model.encode(query).tolist()
        cr         = collection.query(query_embeddings=[query_emb], n_results=min(n, 3))

        for doc, file_id in zip(cr["documents"][0], cr["ids"][0]):
            results.append(f"[Note — {file_id}]\n{doc}")
    except Exception:
        pass

    # --- Validated memories (<vault>/Memories/*.md) ---
    memories = load_all_memories()

    if memories:
        q_emb   = model.encode([query])
        m_embs  = model.encode([m["content"] for m in memories])
        scores  = cosine_similarity(q_emb, m_embs)[0]
        top     = np.argsort(scores)[::-1][:n]

        for idx in top:
            if scores[idx] > 0.3:
                results.append(f"[Memory — {memories[idx]['file']}]\n{memories[idx]['content']}")

    if not results:
        return "No memory found for this query."

    return "\n\n".join(results)


@mcp.tool()
def count_memories() -> str:
    """
    Returns how many memories are stored and how many are pending review.
    """
    memories = load_all_memories()
    total    = len(memories)

    inbox   = Path(__file__).parent / ".data/inbox/memories_to_review.md"
    pending = 0

    if inbox.exists():
        pending = sum(1 for l in inbox.read_text(encoding="utf-8").splitlines() if l.startswith("- [ ] "))

    return f"Total: {total} memories | Pending review: {pending}"


@mcp.tool()
def extract_memories(conversation: str) -> str:
    """
    Extract the important memories from a conversation into the inbox.
    Triggers a SINGLE API call (Gemini). Use at the end of a conversation.
    """
    if not conversation.strip():
        return "Error: empty conversation."

    conv_path = Path(__file__).parent / "conversation.txt"
    conv_path.write_text(conversation, encoding="utf-8")

    try:
        result = subprocess.run(
            [VENV_PYTHON, str(Path(__file__).parent / "memory_extract.py")],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            return f"Extraction error: {result.stderr}"

        return "Memories extracted and saved to your Obsidian vault."

    except subprocess.TimeoutExpired:
        return "Timeout: extraction took too long."


# ======================
# LAUNCH
# ======================

if __name__ == "__main__":
    mcp.run()
