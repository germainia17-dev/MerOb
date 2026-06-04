"""
memory_auto_review.py
─────────────────────
Traite automatiquement les mémoires extraites et les écrit
DIRECTEMENT dans le vault Obsidian DigitBrain, au format tableau.

  - NEW      → ajoutée (avec date) dans la bonne note du vault
  - DOUBLON  → ignorée silencieusement
  - UPDATE   → l'ancienne ligne est remplacée

Classement par similarité sémantique vers les notes existantes.
Si le classement est trop incertain → note "00 À trier.md".
Zéro appel API. Zéro interaction humaine.

Importable : les helpers (parse_note, write_note, detect_category…) peuvent
être réutilisés ailleurs. Le pipeline ne s'exécute que via __main__.
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

DOUBLON_THRESHOLD = 0.85   # ≥ → doublon certain
UPDATE_THRESHOLD  = 0.60   # entre les deux → mise à jour
TRIAGE_THRESHOLD  = 0.25   # classement < seuil → note "À trier"

TRIAGE_NOTE = "00 À trier.md"

DEFAULT_VAULT = (
    "/Users/MacBook/Library/Mobile Documents/iCloud~md~obsidian/"
    "Documents/DigitBrain/DigitBrain/DIGITBRAIN"
)
VAULT = Path(os.getenv("OBSIDIAN_VAULT", DEFAULT_VAULT))

inbox_path = Path("AI_OS/Inbox/memories_to_review.md")
log_path   = Path("AI_OS/Inbox/dernier_ajout.md")

# ======================
# CATÉGORIES = NOTES DU VAULT
# Descriptions affinées pour un classement plus précis.
# La clé est le chemin RELATIF dans le vault.
# ======================

CATEGORIES = {
    "05 Identity.md": (
        "qui est la personne : nom, prénom, âge, ville, lycée, classe STI2D, "
        "apparence physique, taille en cm, corpulence, coupe de cheveux, look, "
        "style vestimentaire, style personnel, "
        "loisirs, passions, temps libre, ski, snowboard, gaming, jeux vidéo préférés, "
        "musique écoutée, rap, artistes, "
        "habitudes personnelles, goûts, préférences de vie"
    ),
    "03 Projects.md": (
        "un projet concret que la personne construit ou développe : "
        "prothèse paralympique, impression 3D, assistant IA local, AI OS, "
        "application, prototype, démo, livrable, "
        "objectif de projet, but à atteindre, certification visée, "
        "deadline, événement à préparer comme VivaTech"
    ),
    "04 Thinking.md": (
        "une réflexion, une décision prise, un choix d'architecture, "
        "une idée ou piste à explorer, un questionnement, une stratégie, "
        "une considération, un raisonnement, une prise de position"
    ),
    "01 Learnig.md": (
        "une connaissance technique apprise, un concept compris, une leçon, "
        "RAG, embeddings, vecteurs, similarité cosinus, tokens, "
        "principe d'ingénierie logicielle, notion d'intelligence artificielle, "
        "savoir réutilisable, explication d'un mécanisme"
    ),
    "Intelligence atrificial/Outils.md": (
        "un outil ou une technologie utilisée : logiciel, application, "
        "langage de programmation, framework, bibliothèque, script, "
        "Obsidian, Python, FastAPI, ChromaDB, Gemini, Claude, Claude Code, ChatGPT, "
        "Raspberry Pi, n8n, Micro:bit, Adalo, VS Code, ContextOptimizer"
    ),
    "06 Mistakes.md": (
        "un défaut personnel, un point faible, une mauvaise habitude, "
        "une difficulté récurrente, un problème de comportement : "
        "éparpillement, dispersion, procrastination, distraction, "
        "difficulté à terminer les projets, manque de discipline, perte de temps"
    ),
    "07 Sources.md": (
        "une source ou référence externe : lien web, URL, article, "
        "vidéo YouTube, documentation, livre, tutoriel, ressource à consulter"
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
# FORMAT TABLEAU
# ======================

def parse_note(file_path: Path) -> list:
    """Lit une note au format tableau → liste de {date, memory}."""
    rows = []
    if not file_path.exists():
        return rows

    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        # Ignorer l'en-tête et la ligne de séparation
        if cells[0].lower() == "date":
            continue
        if set(cells[0]) <= {"-", ":", " "}:
            continue
        rows.append({"date": cells[0], "memory": cells[1]})
    return rows


def write_note(file_path: Path, title: str, rows: list) -> None:
    """Écrit une note au format : titre + tableau Date | Mémoire."""
    lines = [f"# {title}", "", "| Date | Mémoire |", "| --- | --- |"]
    for r in rows:
        mem = r["memory"].replace("|", "/").strip()
        lines.append(f"| {r['date']} | {mem} |")
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def is_junk(memory: str) -> bool:
    """Détecte les fragments inutiles : titres vides, '...', lignes trop courtes.
    Ex : '**Loisirs et intérêts :**' est un en-tête, pas une mémoire."""
    m = memory.strip()
    if not m or m in ("...", "…"):
        return True
    stripped = m.replace("*", "").strip()
    # Un fragment de titre se termine par ":" sans contenu après
    if stripped.endswith(":"):
        return True
    # Trop court pour être une vraie information
    if len(stripped) < 4:
        return True
    return False


def detect_category(memory: str) -> str:
    """Classe la mémoire vers la note la plus proche.
    Si le score est trop bas → note 'À trier'."""
    emb    = model.encode([memory])
    scores = cosine_similarity(emb, _category_embs)[0]
    idx    = int(np.argmax(scores))
    if float(scores[idx]) < TRIAGE_THRESHOLD:
        return TRIAGE_NOTE
    return _category_keys[idx]


def add_memory(memory: str, rel_path: str, date: str) -> str:
    file_path = VAULT / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)

    rows  = parse_note(file_path)
    clean = memory.replace("|", "/").strip()

    if any(r["memory"] == clean for r in rows):
        return "duplicate"

    rows.append({"date": date, "memory": memory})
    write_note(file_path, Path(rel_path).stem, rows)
    return "added"


def update_memory(rel_path: str, old: str, new: str, date: str) -> bool:
    file_path = VAULT / rel_path
    rows = parse_note(file_path)
    old_clean = old.replace("|", "/").strip()

    found = False
    for r in rows:
        if r["memory"] == old_clean:
            r["memory"] = new
            r["date"]   = date
            found = True
            break

    if not found:
        return False

    write_note(file_path, Path(rel_path).stem, rows)
    return True


def get_existing_memories() -> list:
    """Toutes les mémoires déjà présentes dans les notes de catégorie."""
    existing = []
    for rel in _category_keys + [TRIAGE_NOTE]:
        for r in parse_note(VAULT / rel):
            existing.append({"file": rel, "memory": r["memory"]})
    return existing


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
# PIPELINE PRINCIPAL
# ======================

def main():
    if not inbox_path.exists():
        print("Aucune inbox trouvée.")
        return

    if not VAULT.exists():
        print(f"Erreur : vault introuvable → {VAULT}")
        sys.exit(1)

    content = inbox_path.read_text(encoding="utf-8")
    raw_memories = []
    skipped_junk = 0
    for line in content.splitlines():
        if line.startswith("- [ ] "):
            memory = line.replace("- [ ] ", "").strip()
            if not memory:
                continue
            if is_junk(memory):
                skipped_junk += 1
                continue
            raw_memories.append(memory)

    if skipped_junk:
        print(f"→ {skipped_junk} fragment(s) inutile(s) ignoré(s)")

    if not raw_memories:
        print("Aucune mémoire à traiter.")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n→ {len(raw_memories)} mémoire(s) détectées dans l'Inbox")
    print(f"→ Vault : {VAULT}")

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
            print(f"  [DOUBLON]  {memory[:65]}")
            continue

        if classification == "UPDATE":
            ok = update_memory(match["file"], match["memory"], memory, today)
            if ok:
                updated_list.append({"new": memory, "old": match["memory"], "file": match["file"]})
                for m in existing_memories:
                    if m["memory"] == match["memory"]:
                        m["memory"] = memory
                print(f"  [UPDATE]   {memory[:65]}")
                continue
            # sinon → fallback NEW

        # NEW (ou UPDATE qui a échoué)
        cat     = detect_category(memory)
        outcome = add_memory(memory, cat, today)
        if outcome == "added":
            added_list.append({"memory": memory, "file": cat})
            existing_memories.append({"file": cat, "memory": memory})
            category_counts[cat] = category_counts.get(cat, 0) + 1
            tag = "À TRIER" if cat == TRIAGE_NOTE else Path(cat).stem
            print(f"  [NEW → {tag}]  {memory[:65]}")
        else:
            duplicate_list.append(memory)
            print(f"  [IGNORÉE]  {memory[:65]}")

    write_log(raw_memories, added_list, updated_list, duplicate_list)
    print_summary(raw_memories, added_list, updated_list, duplicate_list, category_counts)


def write_log(raw, added, updated, duplicates):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Dernier ajout — {now}",
        "",
        f"**Traitées** : {len(raw)}  |  "
        f"**Ajoutées** : {len(added)}  |  "
        f"**Mises à jour** : {len(updated)}  |  "
        f"**Doublons ignorés** : {len(duplicates)}",
        "",
    ]

    if added:
        lines += ["## ✅ Nouvelles mémoires", ""]
        for item in added:
            lines.append(f"- **{Path(item['file']).stem}** — {item['memory']}")
        lines.append("")

    if updated:
        lines += ["## 🔄 Mises à jour", ""]
        for item in updated:
            lines.append(f"- **{Path(item['file']).stem}** — {item['new']}")
            lines.append(f"  *(remplace : {item['old']})*")
        lines.append("")

    if duplicates:
        lines += ["## ⏭ Doublons ignorés", ""]
        for m in duplicates:
            lines.append(f"- {m}")
        lines.append("")

    log_path.write_text("\n".join(lines), encoding="utf-8")


def print_summary(raw, added, updated, duplicates, category_counts):
    print(f"\n===== RÉSUMÉ =====")
    print(f"Traitées       : {len(raw)}")
    print(f"Nouvelles      : {len(added)}")
    print(f"Mises à jour   : {len(updated)}")
    print(f"Doublons       : {len(duplicates)}")
    print(f"Appels API     : 0")

    if category_counts:
        print("\nClassement dans le vault :")
        for cat, count in category_counts.items():
            tag = "À trier" if cat == TRIAGE_NOTE else Path(cat).stem
            print(f"  - {tag} : {count}")

    print(f"\nNotes mises à jour dans Obsidian (DigitBrain) ✅")
    print(f"Log : AI_OS/Inbox/dernier_ajout.md")


if __name__ == "__main__":
    main()
