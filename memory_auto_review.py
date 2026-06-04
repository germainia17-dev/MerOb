"""
memory_auto_review.py
─────────────────────
Traite automatiquement les mémoires extraites et les écrit
DIRECTEMENT dans le vault Obsidian DigitBrain.

  - NEW      → ajoutée dans la bonne note du vault
  - DOUBLON  → ignorée silencieusement
  - UPDATE   → l'ancienne ligne est remplacée

Classement par similarité sémantique vers les notes existantes du vault.
Zéro appel API. Zéro interaction humaine.
Un log lisible est écrit dans AI_OS/Inbox/dernier_ajout.md.
"""

from pathlib import Path
from datetime import datetime
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os
import sys

# ======================
# CONFIG
# ======================

DOUBLON_THRESHOLD = 0.85
UPDATE_THRESHOLD  = 0.60

# Vault Obsidian (surchargeable via la variable d'env OBSIDIAN_VAULT)
DEFAULT_VAULT = (
    "/Users/MacBook/Library/Mobile Documents/iCloud~md~obsidian/"
    "Documents/DigitBrain/DigitBrain/DIGITBRAIN"
)
VAULT = Path(os.getenv("OBSIDIAN_VAULT", DEFAULT_VAULT))

inbox_path = Path("AI_OS/Inbox/memories_to_review.md")
log_path   = Path("AI_OS/Inbox/dernier_ajout.md")

# ======================
# CATÉGORIES = NOTES DU VAULT
# Chaque note existante du vault est décrite en langage naturel.
# La mémoire est comparée vectoriellement à chaque description.
# La clé est le chemin RELATIF dans le vault.
# ======================

CATEGORIES = {
    "05 Identity.md": (
        "identité personnelle, nom, âge, ville, école, lycée, situation familiale, "
        "apparence physique, taille, style vestimentaire, coupe de cheveux, personnalité, "
        "loisirs, passions, ski, snowboard, gaming, jeux vidéo, musique, rap, hobby, "
        "habitudes, routine, préférence personnelle"
    ),
    "03 Projects.md": (
        "projet personnel, développement, construction, prototype, prothèse, "
        "impression 3D, AI OS, assistant IA, application, pipeline, démo, "
        "objectif, ambition, but à atteindre, certification, événement futur, VivaTech, "
        "ce que la personne veut accomplir"
    ),
    "04 Thinking.md": (
        "réflexion, décision prise, choix, idée, piste à explorer, questionnement, "
        "brainstorming, préoccupation, analyse, considération, stratégie, planification"
    ),
    "01 Learnig.md": (
        "connaissance acquise, concept appris, apprentissage, compréhension, leçon, "
        "RAG, embeddings, vecteurs, cosine similarity, intelligence artificielle, "
        "notion technique, principe d'ingénierie"
    ),
    "Intelligence atrificial/Outils.md": (
        "outil, logiciel, technologie, langage de programmation, framework, script, "
        "Obsidian, Python, FastAPI, ChromaDB, Gemini, Claude, Claude Code, ChatGPT, "
        "Raspberry Pi, n8n, Micro:bit, Adalo, VS Code, ContextOptimizer"
    ),
    "06 Mistakes.md": (
        "erreur, point faible, difficulté, défaut, problème personnel, mauvaise habitude, "
        "éparpillement, procrastination, distraction, manque de suivi, "
        "difficulté à terminer, ce qui ne va pas"
    ),
    "07 Sources.md": (
        "source, référence, lien, article, vidéo, documentation, ressource externe, "
        "citation, site web, bibliographie"
    ),
}

_category_keys  = list(CATEGORIES.keys())
_category_descs = list(CATEGORIES.values())

# ======================
# CHARGEMENT MODÈLE
# ======================

model = SentenceTransformer("all-MiniLM-L6-v2")
_category_embs = model.encode(_category_descs)

# ======================
# LECTURE INBOX
# ======================

if not inbox_path.exists():
    print("Aucune inbox trouvée.")
    sys.exit(0)

if not VAULT.exists():
    print(f"Erreur : vault introuvable → {VAULT}")
    sys.exit(1)

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
print(f"→ Vault : {VAULT}")

# ======================
# OUTILS
# ======================

def get_existing_memories():
    """Lit les mémoires déjà présentes dans les notes du vault."""
    existing = []
    for rel_path in _category_keys:
        file_path = VAULT / rel_path
        if not file_path.exists():
            continue
        for line in file_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("- "):
                memory = line[2:].strip()
                if memory:
                    existing.append({"file": rel_path, "memory": memory})
    return existing


def detect_category(memory: str) -> str:
    """Classe la mémoire par similarité sémantique vers une note du vault.
    Renvoie toujours la note la plus proche (jamais 'Other')."""
    memory_emb = model.encode([memory])
    scores     = cosine_similarity(memory_emb, _category_embs)[0]
    best_idx   = int(np.argmax(scores))
    return _category_keys[best_idx]


def add_memory(memory: str, rel_path: str) -> str:
    file_path = VAULT / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)

    title    = Path(rel_path).stem
    existing = file_path.read_text(encoding="utf-8") if file_path.exists() else ""

    if f"- {memory}" in existing:
        return "duplicate"

    # Si la note est vide, on lui donne un titre propre
    if not existing.strip():
        existing = f"# {title}\n\n"

    file_path.write_text(existing.rstrip("\n") + f"\n- {memory}\n", encoding="utf-8")
    return "added"


def update_memory(rel_path: str, old: str, new: str) -> bool:
    file_path = VAULT / rel_path
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
        print(f"  [DOUBLON]  {memory[:70]}")
        continue

    if classification == "UPDATE":
        ok = update_memory(match["file"], match["memory"], memory)
        if ok:
            updated_list.append({"new": memory, "old": match["memory"], "file": match["file"]})
            for m in existing_memories:
                if m["memory"] == match["memory"]:
                    m["memory"] = memory
            print(f"  [UPDATE]   {memory[:70]}")
        else:
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
        print(f"  [NEW → {Path(cat).stem}]  {memory[:70]}")
    else:
        duplicate_list.append(memory)
        print(f"  [IGNORÉE]  {memory[:70]}")


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
        lines.append(f"- **{Path(item['file']).stem}** — {item['memory']}")
    lines.append("")

if updated_list:
    lines.append("## 🔄 Mises à jour")
    lines.append("")
    for item in updated_list:
        lines.append(f"- **{Path(item['file']).stem}** — {item['new']}")
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
    print("\nClassement dans le vault :")
    for cat, count in category_counts.items():
        print(f"  - {Path(cat).stem} : {count}")

print(f"\nNotes mises à jour dans Obsidian (DigitBrain) ✅")
print(f"Log : AI_OS/Inbox/dernier_ajout.md")
