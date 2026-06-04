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
from sklearn.cluster import AgglomerativeClustering
import numpy as np
import json
import re
import os
import sys

# ======================
# CONFIG
# ======================

DOUBLON_THRESHOLD = 0.92   # ≥ → doublon certain (plus strict car notes individuelles)
UPDATE_THRESHOLD  = 0.70   # entre les deux → mise à jour
RELATED_N         = 2      # nombre de liens vers mémoires proches

# Seuil de confiance de classement (RÉGLAGE CLÉ de la Phase B) :
#   score ≥ seuil  → la mémoire rejoint une catégorie fixe (match confiant)
#   score < seuil  → la mémoire part dans "À trier" = pool de découverte
# Plus le seuil est HAUT, plus l'IA met de mémoires de côté pour créer de
# nouvelles catégories (mais plus le 'À trier' se remplit). Vraies mémoires de
# catégorie ≈ 0.46 ; sujets étrangers ≈ 0.36-0.44. 0.40 = compromis prudent.
CONFIDENT_THRESHOLD = 0.40

# --- Phase B : découverte auto de catégories (mode hybride) ---
NEW_CAT_MIN_SIZE   = 3     # nb min de mémoires "À trier" similaires pour créer une catégorie
NEW_CAT_DISTANCE   = 0.56  # distance cosinus max intra-cluster (linkage complete)
# Filtre anti-intrus : similarité moyenne min aux autres membres du cluster.
# Volontairement bas (0.40) — il écarte les intrus évidents sans sacrifier les
# vrais membres. Une mémoire vraiment limite peut occasionnellement rejoindre une
# catégorie voisine : c'est récupérable en 1 clic et s'auto-corrige avec plus de données.
NEW_CAT_MEMBER_SIM = 0.40

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

# Catégories découvertes par l'IA (mode hybride), persistées entre les runs.
# Format : { "NomCatégorie": "description = mémoires fondatrices concaténées" }
DISCOVERED_PATH = Path("AI_OS/discovered_categories.json")


def load_discovered() -> dict:
    if DISCOVERED_PATH.exists():
        try:
            return json.loads(DISCOVERED_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_discovered(d: dict) -> None:
    DISCOVERED_PATH.parent.mkdir(parents=True, exist_ok=True)
    DISCOVERED_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


DISCOVERED = load_discovered()

# ======================
# CHARGEMENT MODÈLE
# ======================

model = SentenceTransformer("all-MiniLM-L6-v2")


def build_category_index():
    """Index de classification = catégories fixes + catégories découvertes."""
    keys  = list(CATEGORIES.keys()) + list(DISCOVERED.keys())
    descs = list(CATEGORIES.values()) + list(DISCOVERED.values())
    embs  = model.encode(descs)
    return keys, embs


_category_keys, _category_embs = build_category_index()


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
    if float(scores[idx]) < CONFIDENT_THRESHOLD:
        return TRIAGE_CAT
    return _category_keys[idx]


# ======================
# PHASE B — DÉCOUVERTE DE CATÉGORIES (hybride)
# ======================

# Mots vides français à ignorer pour nommer une catégorie
_FR_STOP = {
    "dans", "pour", "avec", "cette", "celui", "celle", "leur", "leurs", "elle",
    "être", "avoir", "faire", "plus", "moins", "très", "alors", "donc", "mais",
    "comme", "tout", "tous", "toute", "toutes", "aussi", "entre", "sans", "sous",
    "chez", "vers", "depuis", "pendant", "selon", "afin", "lorsqu", "quand",
    "utilisateur", "user", "germain", "veut", "doit", "peut", "ses", "son", "une",
    "des", "les", "que", "qui", "est", "sont", "aux", "par", "sur", "the",
}


def name_cluster(texts: list) -> str:
    """Nomme une catégorie à partir du mot fort le plus fréquent (0 API).
    Phase C pourra remplacer ce nommage par un appel Gemini."""
    counts = {}
    for t in texts:
        for w in re.findall(r"[a-zàâäéèêëïîôùûüçœ]{4,}", t.lower()):
            if w in _FR_STOP:
                continue
            counts[w] = counts.get(w, 0) + 1
    if not counts:
        return "Divers"
    top = max(counts, key=counts.get)
    return top.capitalize()


def discover_categories(triage_notes: list) -> dict:
    """Cherche des grappes denses dans le pool 'À trier'.
    Retourne {nom_catégorie: [notes]} pour chaque grappe assez grosse."""
    if len(triage_notes) < NEW_CAT_MIN_SIZE:
        return {}

    texts = [n["memory"] for n in triage_notes]
    embs  = model.encode(texts)

    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=NEW_CAT_DISTANCE,
        metric="cosine",
        linkage="complete",
    )
    labels = clustering.fit_predict(embs)

    # Regroupe (note, embedding) par cluster
    clusters = {}
    for note, emb, label in zip(triage_notes, embs, labels):
        clusters.setdefault(int(label), []).append((note, emb))

    discovered = {}
    for items in clusters.values():
        if len(items) < NEW_CAT_MIN_SIZE:
            continue

        # Filtre les intrus : similarité moyenne de chaque membre aux AUTRES
        # (leave-one-out) — robuste car un intrus ne peut pas gonfler son propre score
        member_embs = np.array([e for _, e in items])
        sim_matrix  = cosine_similarity(member_embs)
        np.fill_diagonal(sim_matrix, np.nan)
        mean_to_others = np.nanmean(sim_matrix, axis=1)
        kept = [note for (note, _), s in zip(items, mean_to_others) if s >= NEW_CAT_MEMBER_SIM]

        if len(kept) < NEW_CAT_MIN_SIZE:
            continue

        name = name_cluster([m["memory"] for m in kept])
        # éviter une collision avec une catégorie existante
        if name in CATEGORIES or name in DISCOVERED or name in discovered:
            name = f"{name} (auto)"
        discovered[name] = kept
    return discovered


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

    # --- Phase B : l'IA fait émerger de nouvelles catégories ---
    created_cats = []
    triage_notes = [n for n in existing_notes if n["category"] == TRIAGE_CAT]
    new_cats = discover_categories(triage_notes)

    if new_cats:
        for name, members in new_cats.items():
            # La description sert aux classifications futures
            DISCOVERED[name] = " / ".join(m["memory"] for m in members)[:500]
            for m in members:
                m["category"] = name
                others  = [x for x in existing_notes if x["memory"] != m["memory"]]
                related = find_related(m["memory"], others)
                write_memory_note(m["memory"], name, today, related)
            created_cats.append((name, len(members)))
            print(f"  [NOUVELLE CATÉGORIE → {name}]  {len(members)} mémoires regroupées")
        save_discovered(DISCOVERED)

    # Met à jour tous les hubs de catégorie
    all_cats = set(n["category"] for n in existing_notes)
    for cat in all_cats:
        update_category_hub(cat, existing_notes)

    # Nettoie les hubs devenus vides (ex : 'À trier' vidé par la découverte)
    if CATEGORIES_DIR.exists():
        for hub in CATEGORIES_DIR.glob("*.md"):
            if hub.stem not in all_cats:
                hub.unlink()

    write_log(raw_memories, added_list, updated_list, duplicate_list, created_cats)
    print_summary(raw_memories, added_list, updated_list, duplicate_list, created_cats)


def write_log(raw, added, updated, duplicates, created_cats=None):
    created_cats = created_cats or []
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
    if created_cats:
        lines += ["## 🆕 Nouvelles catégories créées par l'IA", ""]
        for name, count in created_cats:
            lines.append(f"- **[[{name}]]** — {count} mémoires regroupées")
        lines.append("")
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


def print_summary(raw, added, updated, duplicates, created_cats=None):
    created_cats = created_cats or []
    print(f"\n===== RÉSUMÉ =====")
    print(f"Traitées       : {len(raw)}")
    print(f"Nouvelles notes: {len(added)}")
    print(f"Mises à jour   : {len(updated)}")
    print(f"Doublons       : {len(duplicates)}")
    if created_cats:
        print(f"Catégories créées par l'IA : {len(created_cats)} "
              f"({', '.join(n for n, _ in created_cats)})")
    print(f"Appels API     : 0")
    print(f"\nNotes créées dans : Memories/")
    print(f"Hubs mis à jour dans : Categories/")
    print(f"Log : AI_OS/Inbox/dernier_ajout.md")


if __name__ == "__main__":
    main()
