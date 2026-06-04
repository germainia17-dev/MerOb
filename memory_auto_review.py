"""
memory_auto_review.py
─────────────────────
Traite automatiquement les mémoires extraites :
  - NEW      → ajoutées directement dans AI_OS/Memory/[Catégorie].md
  - DOUBLON  → ignorées silencieusement
  - UPDATE   → l'ancienne ligne est remplacée automatiquement

Zéro appel API. Zéro interaction humaine.
Un log est écrit dans AI_OS/Inbox/dernier_ajout.md (lisible dans Obsidian).
"""

from pathlib import Path
from datetime import datetime
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import sys

# ======================
# CONFIG
# ======================

DOUBLON_THRESHOLD = 0.85
UPDATE_THRESHOLD  = 0.60

inbox_path = Path("AI_OS/Inbox/memories_to_review.md")
memory_dir = Path("AI_OS/Memory")
log_path   = Path("AI_OS/Inbox/dernier_ajout.md")

memory_dir.mkdir(parents=True, exist_ok=True)

# ======================
# CATÉGORIES SÉMANTIQUES
# Chaque catégorie est décrite en langage naturel.
# La mémoire est comparée vectoriellement à chaque description.
# Pas de mots-clés hardcodés — robuste aux reformulations.
# ======================

CATEGORIES = {
    "Identity.md": (
        "identité personnelle, nom, âge, ville, école, lycée, situation familiale, "
        "apparence physique, style vestimentaire, personnalité, profil"
    ),
    "Projects.md": (
        "projet personnel, développement logiciel, construction, prototype, "
        "impression 3D, prothèse, application, pipeline, AI OS, démo, VivaTech"
    ),
    "Goals.md": (
        "objectif, ambition, motivation, souhait, aspiration, but à atteindre, "
        "certification, événement futur, ce que la personne veut accomplir"
    ),
    "Tools.md": (
        "outil, logiciel, technologie, langage de programmation, framework, "
        "Obsidian, Python, FastAPI, ChromaDB, Gemini, Claude, ChatGPT, Raspberry Pi, "
        "n8n, Micro:bit, Adalo, VS Code"
    ),
    "Knowledge.md": (
        "connaissance acquise, concept appris, compréhension, apprentissage, "
        "RAG, embeddings, vecteurs, cosine similarity, modèle de langage, IA"
    ),
    "Decisions.md": (
        "décision prise, choix effectué, validation, intégration choisie, "
        "option retenue, préférence confirmée"
    ),
    "Ideas.md": (
        "idée, piste à explorer, fonctionnalité à ajouter, amélioration possible, "
        "concept à tester, inspiration, brainstorming"
    ),
    "Tasks.md": (
        "tâche à faire, todo, action à réaliser, corriger, tester, implémenter, "
        "déployer, à compléter, prochaine étape"
    ),
    "Interests.md": (
        "loisir, intérêt, passion, hobby, jeux vidéo, sport, musique, lecture, "
        "gaming, réseaux sociaux, activité personnelle"
    ),
    "Habits.md": (
        "habitude, routine, comportement récurrent, façon de travailler, "
        "préférence de travail, organisation personnelle, méthode"
    ),
}

_category_keys  = list(CATEGORIES.keys())
_category_descs = list(CATEGORIES.values())

# ======================
# CHARGEMENT MODÈLE
# ======================

model = SentenceTransformer("all-MiniLM-L6-v2")

# Encodage des catégories (une seule fois, après chargement du modèle)
_category_embs = model.encode(_category_descs)

# ======================
# LECTURE INBOX
# ======================

if not inbox_path.exists():
    print("Aucune inbox trouvée.")
    sys.exit(0)

content = inbox_path.read_text(encoding="utf-8")
raw_memories = []

for line in content.splitlines():
    if line.startswith("- [ ] "):
        memory = line.replace("- [ ] ", "").strip()
        if memory:
            raw_memories.append(memory)

if not raw_memories:
    print("Aucune mémoire à traiter.")
    sys.exit(0)

print(f"\n→ {len(raw_memories)} mémoire(s) détectées dans l'Inbox")

# ======================
# OUTILS
# ======================

def get_existing_memories():
    existing = []
    for file in memory_dir.glob("*.md"):
        for line in file.read_text(encoding="utf-8").splitlines():
            if line.startswith("- "):
                memory = line[2:].strip()
                if memory:
                    existing.append({"file": file.name, "memory": memory})
    return existing


def detect_category(memory: str) -> str:
    """Classe la mémoire par similarité sémantique avec les descriptions de catégories."""
    memory_emb = model.encode([memory])
    scores     = cosine_similarity(memory_emb, _category_embs)[0]
    best_idx   = int(np.argmax(scores))
    best_score = float(scores[best_idx])

    if best_score < 0.20:
        return "Other.md"

    return _category_keys[best_idx]


def add_memory(memory: str, filename: str) -> str:
    file_path = memory_dir / filename
    title     = filename.replace(".md", "")
    existing  = file_path.read_text(encoding="utf-8") if file_path.exists() else f"# {title}\n\n"

    if f"- {memory}" in existing:
        return "duplicate"

    file_path.write_text(existing.rstrip("\n") + f"\n- {memory}\n", encoding="utf-8")
    return "added"


def update_memory(filename: str, old: str, new: str) -> bool:
    file_path = memory_dir / filename
    if not file_path.exists():
        return False

    content = file_path.read_text(encoding="utf-8")
    if f"- {old}" not in content:
        return False

    file_path.write_text(content.replace(f"- {old}", f"- {new}"), encoding="utf-8")
    return True


def reconcile(new_memory: str, existing: list) -> dict:
    if not existing:
        return {"classification": "NEW", "match": None, "score": 0.0}

    texts        = [m["memory"] for m in existing]
    new_emb      = model.encode([new_memory])
    existing_emb = model.encode(texts)
    scores       = cosine_similarity(new_emb, existing_emb)[0]
    best_idx     = int(np.argmax(scores))
    best_score   = float(scores[best_idx])
    best_match   = existing[best_idx]

    if best_score >= DOUBLON_THRESHOLD:
        return {"classification": "DOUBLON", "match": best_match, "score": best_score}
    elif best_score >= UPDATE_THRESHOLD:
        return {"classification": "UPDATE",  "match": best_match, "score": best_score}
    else:
        return {"classification": "NEW",     "match": None,       "score": best_score}


# ======================
# TRAITEMENT AUTO
# ======================

existing_memories = get_existing_memories()

added_list      = []
updated_list    = []
duplicate_list  = []
category_counts = {}

for memory in raw_memories:
    result         = reconcile(memory, existing_memories)
    classification = result["classification"]
    match          = result["match"]

    if classification == "DOUBLON":
        duplicate_list.append(memory)
        print(f"  [DOUBLON]  {memory[:80]}")
        continue

    if classification == "UPDATE":
        ok = update_memory(match["file"], match["memory"], memory)
        if ok:
            updated_list.append({"new": memory, "old": match["memory"], "file": match["file"]})
            for m in existing_memories:
                if m["memory"] == match["memory"]:
                    m["memory"] = memory
            print(f"  [UPDATE]   {memory[:80]}")
        else:
            # Fallback → ajouter comme NEW
            cat     = detect_category(memory)
            outcome = add_memory(memory, cat)
            if outcome == "added":
                added_list.append({"memory": memory, "file": cat})
                existing_memories.append({"file": cat, "memory": memory})
                category_counts[cat] = category_counts.get(cat, 0) + 1
        continue

    # NEW
    cat     = detect_category(memory)
    outcome = add_memory(memory, cat)

    if outcome == "added":
        added_list.append({"memory": memory, "file": cat})
        existing_memories.append({"file": cat, "memory": memory})
        category_counts[cat] = category_counts.get(cat, 0) + 1
        print(f"  [NEW → {cat.replace('.md','')}]  {memory[:80]}")
    else:
        duplicate_list.append(memory)
        print(f"  [IGNORÉE]  {memory[:80]}")


# ======================
# LOG OBSIDIAN
# ======================

now = datetime.now().strftime("%Y-%m-%d %H:%M")
lines = [
    f"# Dernier ajout — {now}",
    "",
    f"**Traitées** : {len(raw_memories)}  |  "
    f"**Ajoutées** : {len(added_list)}  |  "
    f"**Mises à jour** : {len(updated_list)}  |  "
    f"**Doublons ignorés** : {len(duplicate_list)}",
    "",
]

if added_list:
    lines.append("## ✅ Nouvelles mémoires")
    lines.append("")
    for item in added_list:
        lines.append(f"- **{item['file'].replace('.md','')}** — {item['memory']}")
    lines.append("")

if updated_list:
    lines.append("## 🔄 Mises à jour")
    lines.append("")
    for item in updated_list:
        lines.append(f"- **{item['file'].replace('.md','')}** — {item['new']}")
        lines.append(f"  *(remplace : {item['old']})*")
    lines.append("")

if duplicate_list:
    lines.append("## ⏭ Doublons ignorés")
    lines.append("")
    for m in duplicate_list:
        lines.append(f"- {m}")
    lines.append("")

log_path.write_text("\n".join(lines), encoding="utf-8")

# ======================
# RÉSUMÉ TERMINAL
# ======================

print(f"\n===== RÉSUMÉ =====")
print(f"Traitées       : {len(raw_memories)}")
print(f"Nouvelles      : {len(added_list)}")
print(f"Mises à jour   : {len(updated_list)}")
print(f"Doublons       : {len(duplicate_list)}")
print(f"Appels API     : 0")

if category_counts:
    print("\nClassement par catégorie :")
    for cat, count in category_counts.items():
        print(f"  - {cat} : {count}")

print(f"\nLog Obsidian   : AI_OS/Inbox/dernier_ajout.md")
print("Mémoires dans  : AI_OS/Memory/")
