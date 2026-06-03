from mcp.server.fastmcp import FastMCP
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import chromadb
import subprocess
import numpy as np
import sys

# ======================
# CONFIG
# ======================

mcp         = FastMCP("AI OS Memory")
model       = SentenceTransformer("all-MiniLM-L6-v2")
chroma      = chromadb.PersistentClient(path=str(Path(__file__).parent / "chroma_db"))
memory_dir  = Path(__file__).parent / "AI_OS/Memory"
VENV_PYTHON = sys.executable


# ======================
# OUTILS MCP
# ======================

@mcp.tool()
def search_memories(query: str, n: int = 5) -> str:
    """
    Cherche dans les notes et mémoires personnelles de l'utilisateur.
    Utilise la recherche vectorielle locale — aucun appel API.
    À appeler en début de conversation pour personnaliser le contexte.
    """
    results = []

    # --- ChromaDB (notes vectorisées) ---
    try:
        collection = chroma.get_collection("notes")
        query_emb  = model.encode(query).tolist()
        cr         = collection.query(query_embeddings=[query_emb], n_results=min(n, 3))

        for doc, file_id in zip(cr["documents"][0], cr["ids"][0]):
            results.append(f"[Note — {file_id}]\n{doc}")
    except Exception:
        pass

    # --- Mémoires validées (AI_OS/Memory/*.md) ---
    memories = []

    for file in memory_dir.glob("*.md"):
        for line in file.read_text(encoding="utf-8").splitlines():
            if line.startswith("- "):
                text = line[2:].strip()
                if text:
                    memories.append({"file": file.name, "content": text})

    if memories:
        q_emb   = model.encode([query])
        m_embs  = model.encode([m["content"] for m in memories])
        scores  = cosine_similarity(q_emb, m_embs)[0]
        top     = np.argsort(scores)[::-1][:n]

        for idx in top:
            if scores[idx] > 0.3:
                results.append(f"[Mémoire — {memories[idx]['file']}]\n{memories[idx]['content']}")

    if not results:
        return "Aucune mémoire trouvée pour cette requête."

    return "\n\n".join(results)


@mcp.tool()
def count_memories() -> str:
    """
    Retourne le nombre de mémoires stockées et combien sont en attente de validation.
    """
    total  = 0
    counts = {}

    for file in memory_dir.glob("*.md"):
        n = sum(1 for l in file.read_text(encoding="utf-8").splitlines() if l.startswith("- "))
        counts[file.name] = n
        total += n

    inbox   = Path(__file__).parent / "AI_OS/Inbox/memories_to_review.md"
    pending = 0

    if inbox.exists():
        pending = sum(1 for l in inbox.read_text(encoding="utf-8").splitlines() if l.startswith("- [ ] "))

    lines = [f"Total : {total} mémoires | En attente : {pending}"]
    for fname, count in counts.items():
        if count > 0:
            lines.append(f"  - {fname} : {count}")

    return "\n".join(lines)


@mcp.tool()
def extract_memories(conversation: str) -> str:
    """
    Extrait les mémoires importantes d'une conversation et les place dans l'Inbox.
    Déclenche UN seul appel API (Gemini). À utiliser en fin de conversation.
    """
    if not conversation.strip():
        return "Erreur : conversation vide."

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
            return f"Erreur extraction : {result.stderr}"

        return "Mémoires extraites → AI_OS/Inbox/memories_to_review.md"

    except subprocess.TimeoutExpired:
        return "Timeout : extraction trop longue."


# ======================
# LANCEMENT
# ======================

if __name__ == "__main__":
    mcp.run()
