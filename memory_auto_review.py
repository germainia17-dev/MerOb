"""
memory_auto_review.py
─────────────────────
Traite automatiquement les mémoires extraites.

Pour chaque mémoire validée :
  - NEW      → une note .md individuelle créée dans Memories/
  - DOUBLON  → ignorée silencieusement
  - UPDATE   → la note existante mise à jour

Chaque note contient :
  - Le texte de la mémoire
  - Sa date d'extraction
  - Un wikilink [[Catégorie]] vers sa catégorie hub
  - Des wikilinks [[Mémoire proche]] vers les 2 mémoires les plus similaires
  → Le graph Obsidian forme un réseau organique

Les notes de catégorie (hub) sont mises à jour automatiquement
avec la liste des mémoires qu'elles contiennent.

Zéro appel API. Zéro interaction humaine.
"""

from pathlib import Path
from datetime import datetime
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re
import os
import sys

# ======================
# CONFIG
# ======================

DOUBLON_THRESHOLD = 0.92   # ≥ → doublon certain (plus strict car notes individuelles)
UPDATE_THRESHOLD  = 0.70   # entre les deux → mise à jour
TRIAGE_THRESHOLD  = 0.25   # classement < seuil → catégorie "À trier"
RELATED_N         = 2      # nombre de liens vers mémoires proches

TRIAGE_CAT = "À trier"

DEFAULT_VAULT = (
    "/Users/MacBook/Library/Mobile Documents/iCloud~md~obsidian/"
    "Documents/DigitBrain/DigitBrain/DIGITBRAIN"
)
VAULT = Path(os.getenv("OBSIDIAN_VAULT", DEFAULT_VAULT))

# Dossiers dans le vault
MEMORIES_DIR = VAULT / "Memories"    # une note par mémoire
CATEGORIES_DIR = VAULT / "Categories"  # notes hub par catégorie

inbox_path = Path("AI_OS/Inbox/memories_to_review.md")
log_path   = Path("AI_OS/Inbox/dernier_ajout.md")

# ======================
# CATÉGORIES SÉMANTIQUES
# ======================

CATEGORIES = {
    "Identité": (
        "qui est la personne : nom, prénom, âge, ville, lycée, classe STI2D, "
        "apparence physique, taille, style vestimentaire, coupe de cheveux, "
        "personnalité, loisirs, passions, ski, snowboard, gaming, jeux vidéo, "
        "musique, rap, habitudes personnelles, goûts, préférences de vie"
    ),
    "Projets": (
        "projet concret construit ou développé : prothèse, impression 3D, "
        "assistant IA, AI OS, application, prototype, démo, livrable, "
        "objectif de projet, certification, deadline, VivaTech"
    ),
    "Réflexions": (
        "décision prise, choix d'architecture, idée à explorer, questionnement, "
        "stratégie, considération, raisonnement, prise de position, analyse"
    ),
    "Apprentissages": (
        "connaissance technique apprise, concept compris, leçon, "
        "RAG, embeddings, vecteurs, tokens, IA, ingénierie logicielle, "
        "notion technique, principe réutilisable"
    ),
    "Outils": (
        "outil ou technologie utilisée : logiciel, langage, framework, script, "
        "Obsidian, Python, FastAPI, ChromaDB, Gemini, Claude, Claude Code, "
        "ChatGPT, Raspberry Pi, n8n, Micro:bit, Adalo, VS Code, ContextOptimizer"
    ),
    "Erreurs": (
        "défaut personnel, point faible, mauvaise habitude, difficulté récurrente, "
        "éparpillement, procrastination, distraction, difficulté à terminer"
    ),
    "Sources": (
        "source externe, lien, URL, article, documentation, ressource à consulter"
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
# UTILITAIRES
# ======================

def slugify(text: str, max_len: int = 50) -> str:
    """Transforme un texte en nom de fichier propre."""
    # Supprime le markdown gras/italique
    text = re.sub(r"\*+", "", text)
    # Supprime les caractères spéciaux, garde lettres/chiffres/espaces
    text = re.sub(r"[^\w\s\-àâäéèêëïîôùûüçœæ]", " ", text, flags=re.UNICODE)
    # Collapse les espaces
    text = re.sub(r"\s+", " ", text).strip()
    # Tronque proprement
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0]
    return text.strip()


def is_junk(memory: str) -> bool:
    """Détecte les fragments inutiles : titres vides, '...', lignes trop courtes."""
    m = memory.strip()
    if not m or m in ("...", "…"):
        return True
    stripped = re.sub(r"\*+", "", m).strip()
    if stripped.endswith(":"):
        return True
    if len(stripped) < 8:
        return True
    return False


def detect_category(memory: str) -> str:
    """Classe la mémoire vers la catégorie la plus proche.
    Retourne TRIAGE_CAT si score trop bas."""
    emb    = model.encode([memory])
    scores = cosine_similarity(emb, _category_embs)[0]
    idx    = int(np.argmax(scores))
    if float(scores[idx]) < TRIAGE_THRESHOLD:
        return TRIAGE_CAT
    return _category_keys[idx]


# ======================
# LECTURE / ÉCRITURE NOTES
# ======================

def get_all_memory_notes() -> list:
    """Lit toutes les notes de mémoire existantes.
    Retourne liste de {slug, memory, category, date, path}."""
    notes = []
    if not MEMORIES_DIR.exists():
        return notes
    for f in MEMORIES_DIR.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        lines = text.splitlines()
        # La mémoire est dans la première ligne non-vide non-frontmatter
        memory_text = ""
        in_front = False
        for line in lines:
            if line.strip() == "---":
                in_front = not in_front
                continue
            if in_front:
                continue
            if line.strip() and not line.startswith("#") and not line.startswith("[["):
                memory_text = line.strip()
                break
        if memory_text:
            # Extraire la catégorie depuis les wikilinks
            cat_match = re.search(r"\[\[([^\]]+)\]\]", text)
            cat = cat_match.group(1) if cat_match else TRIAGE_CAT
            notes.append({
                "slug": f.stem,
                "memory": memory_text,
                "category": cat,
                "path": f,
            })
    return notes


def memory_to_filename(memory: str) -> str:
    """Génère un nom de fichier unique depuis le texte d'une mémoire."""
    slug = slugify(memory, max_len=55)
    return slug + ".md"


def find_related(memory: str, all_notes: list, n: int = RELATED_N) -> list:
    """Trouve les N mémoires les plus proches (excluant les doublons)."""
    if not all_notes:
        return []
    texts = [note["memory"] for note in all_notes]
    mem_emb   = model.encode([memory])
    all_embs  = model.encode(texts)
    scores    = cosine_similarity(mem_emb, all_embs)[0]
    # Exclure la mémoire elle-même (score = 1.0)
    sorted_idx = np.argsort(scores)[::-1]
    related = []
    for idx in sorted_idx:
        if scores[idx] > 0.98:   # c'est la même mémoire
            continue
        if scores[idx] < 0.30:  # trop peu lié
            break
        related.append(all_notes[idx]["slug"])
        if len(related) >= n:
            break
    return related


def write_memory_note(memory: str, category: str, date: str, related_slugs: list) -> Path:
    """Crée ou met à jour la note individuelle d'une mémoire."""
    MEMORIES_DIR.mkdir(parents=True, exist_ok=True)
    filename = memory_to_filename(memory)
    path     = MEMORIES_DIR / filename

    related_links = "  ".join(f"[[{s}]]" for s in related_slugs)

    lines = [
        f"> {memory}",
        "",
        f"**Catégorie :** [[{category}]]",
    ]
    if related_links:
        lines.append(f"**Liens :** {related_links}")
    lines += [
        "",
        f"*Extrait le {date}*",
    ]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def update_category_hub(category: str, all_notes: list) -> None:
    """Met à jour la note hub d'une catégorie avec tous ses membres."""
    CATEGORIES_DIR.mkdir(parents=True, exist_ok=True)
    path = CATEGORIES_DIR / f"{category}.md"

    members = [n for n in all_notes if n["category"] == category]

    lines = [f"# {category}", "", f"*{len(members)} mémoire(s)*", ""]
    for m in members:
        lines.append(f"- [[{m['slug']}]]")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def reconcile(new_memory: str, existing_notes: list) -> dict:
    """Cherche si la mémoire est un doublon ou une mise à jour."""
    if not existing_notes:
        return {"classification": "NEW", "match": None, "score": 0.0}

    texts = [n["memory"] for n in existing_notes]
    new_emb  = model.encode([new_memory])
    all_embs = model.encode(texts)
    scores   = cosine_similarity(new_emb, all_embs)[0]
    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])

    if best_score >= DOUBLON_THRESHOLD:
        return {"classification": "DOUBLON", "match": existing_notes[best_idx], "score": best_score}
    elif best_score >= UPDATE_THRESHOLD:
        return {"classification": "UPDATE",  "match": existing_notes[best_idx], "score": best_score}
    else:
        return {"classification": "NEW",     "match": None,                     "score": best_score}


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

    if not raw_memories:
        print("Aucune mémoire à traiter.")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n→ {len(raw_memories)} mémoire(s) à traiter (+ {skipped_junk} fragment(s) ignoré(s))")
    print(f"→ Vault : {VAULT.name}")

    # Charge les notes existantes
    existing_notes = get_all_memory_notes()
    print(f"→ {len(existing_notes)} notes déjà présentes dans Memories/\n")

    added_list     = []
    updated_list   = []
    duplicate_list = []

    for memory in raw_memories:
        result         = reconcile(memory, existing_notes)
        classification = result["classification"]
        match          = result["match"]

        if classification == "DOUBLON":
            duplicate_list.append(memory)
            print(f"  [DOUBLON]  {memory[:65]}")
            continue

        category = detect_category(memory)

        if classification == "UPDATE" and match:
            # Supprimer l'ancienne note et réécrire
            if match["path"].exists():
                match["path"].unlink()
            # Mettre à jour dans existing_notes pour les liens
            for n in existing_notes:
                if n["memory"] == match["memory"]:
                    n["memory"]   = memory
                    n["category"] = category
                    n["slug"]     = slugify(memory, 55)
            updated_list.append({"new": memory, "old": match["memory"], "category": category})
            print(f"  [UPDATE → {category}]  {memory[:55]}")

        if classification == "NEW" or classification == "UPDATE":
            # Liens vers mémoires proches (sur les notes existantes à ce moment)
            others  = [n for n in existing_notes if n["memory"] != memory]
            related = find_related(memory, others)

            note_path = write_memory_note(memory, category, today, related)

            if classification == "NEW":
                slug = note_path.stem
                existing_notes.append({"slug": slug, "memory": memory,
                                        "category": category, "path": note_path})
                added_list.append({"memory": memory, "category": category, "slug": slug})
                print(f"  [NEW → {category}]  {memory[:55]}")

    # Met à jour tous les hubs de catégorie
    all_cats = set(n["category"] for n in existing_notes)
    for cat in all_cats:
        update_category_hub(cat, existing_notes)

    write_log(raw_memories, added_list, updated_list, duplicate_list)
    print_summary(raw_memories, added_list, updated_list, duplicate_list)


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
        lines += ["## ✅ Nouvelles notes", ""]
        for item in added:
            lines.append(f"- **{item['category']}** — [[{item['slug']}]]")
        lines.append("")
    if updated:
        lines += ["## 🔄 Mises à jour", ""]
        for item in updated:
            lines.append(f"- **{item['category']}** — {item['new'][:60]}")
            lines.append(f"  *(remplace : {item['old'][:60]})*")
        lines.append("")
    if duplicates:
        lines += ["## ⏭ Doublons ignorés", ""]
        for m in duplicates:
            lines.append(f"- {m}")
        lines.append("")
    log_path.write_text("\n".join(lines), encoding="utf-8")


def print_summary(raw, added, updated, duplicates):
    print(f"\n===== RÉSUMÉ =====")
    print(f"Traitées       : {len(raw)}")
    print(f"Nouvelles notes: {len(added)}")
    print(f"Mises à jour   : {len(updated)}")
    print(f"Doublons       : {len(duplicates)}")
    print(f"Appels API     : 0")
    print(f"\nNotes créées dans : Memories/")
    print(f"Hubs mis à jour dans : Categories/")
    print(f"Log : AI_OS/Inbox/dernier_ajout.md")


if __name__ == "__main__":
    main()
