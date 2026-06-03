from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# ======================
# CONFIG
# ======================

DOUBLON_THRESHOLD = 0.85   # au-dessus → doublon certain
UPDATE_THRESHOLD  = 0.60   # entre les deux → potentiel update

model = SentenceTransformer("all-MiniLM-L6-v2")

inbox_path = Path("AI_OS/Inbox/memories_to_review.md")
memory_dir = Path("AI_OS/Memory")

memory_dir.mkdir(parents=True, exist_ok=True)

# ======================
# LECTURE INBOX
# ======================

if not inbox_path.exists():
    print("Erreur : aucun fichier de mémoires à valider trouvé.")
    exit()

content = inbox_path.read_text(encoding="utf-8")

memories = []

for line in content.splitlines():
    if line.startswith("- [ ] "):
        memory = line.replace("- [ ] ", "").strip()
        if memory:
            memories.append(memory)

if not memories:
    print("Aucune mémoire à valider.")
    exit()

# ======================
# OUTILS MÉMOIRE
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


def detect_category(memory):
    text = memory.lower()

    if any(w in text for w in ["décidé", "decision", "décision", "choix", "choisi", "validation", "intégration"]):
        return "Decisions.md"
    if any(w in text for w in ["idée", "ajouter", "fonctionnalité", "piste"]):
        return "Ideas.md"
    if any(w in text for w in ["a appris", "comprend", "connaît", "concept", "rag", "embedding"]):
        return "Knowledge.md"
    if any(w in text for w in ["doit faire", "à faire", "tâche", "todo", "corriger", "tester", "créer"]):
        return "Tasks.md"
    if any(w in text for w in ["projet", "développe", "ai os"]):
        return "Projects.md"
    if any(w in text for w in ["obsidian", "gemini", "claude", "chatgpt", "outil", "python", "vscode"]):
        return "Tools.md"
    if any(w in text for w in ["macbook", "mac ", "ordinateur", "utilisateur travaille"]):
        return "Identity.md"
    if any(w in text for w in ["objectif", "veut", "souhaite", "but"]):
        return "Goals.md"

    return "Other.md"


def add_memory_to_file(memory, filename):
    file_path = memory_dir / filename
    title = filename.replace(".md", "")

    existing = file_path.read_text(encoding="utf-8") if file_path.exists() else f"# {title}\n\n"

    if memory in existing:
        print(f"Déjà existante, ignorée : {memory}")
        return "duplicate"

    file_path.write_text(existing + f"- {memory}\n", encoding="utf-8")
    return "added"


def update_memory_in_file(filename, old_memory, new_memory):
    file_path = memory_dir / filename
    if not file_path.exists():
        print(f"Erreur : fichier introuvable : {filename}")
        return False

    content = file_path.read_text(encoding="utf-8")
    old_line = f"- {old_memory}"

    if old_line not in content:
        print("Erreur : ancienne mémoire introuvable.")
        return False

    file_path.write_text(content.replace(old_line, f"- {new_memory}"), encoding="utf-8")
    return True


# ======================
# RÉCONCILIATION LOCALE
# (zéro appel API)
# ======================

def reconcile_local(new_memory, existing_memories):
    if not existing_memories:
        return {"classification": "NEW", "match": None, "score": 0.0}

    texts = [m["memory"] for m in existing_memories]

    new_emb      = model.encode([new_memory])
    existing_emb = model.encode(texts)

    scores   = cosine_similarity(new_emb, existing_emb)[0]
    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])
    best_match = existing_memories[best_idx]

    if best_score >= DOUBLON_THRESHOLD:
        return {"classification": "DOUBLON", "match": best_match, "score": best_score}
    elif best_score >= UPDATE_THRESHOLD:
        return {"classification": "UPDATE",  "match": best_match, "score": best_score}
    else:
        return {"classification": "NEW",     "match": None,       "score": best_score}


# ======================
# VALIDATION HUMAINE
# ======================

validated = []
rejected  = []
skipped   = []

print("\n===== MÉMOIRES À VALIDER =====\n")

for index, memory in enumerate(memories, start=1):
    print(f"\n{index}. {memory}")
    choice = input("Accepter (o) | Refuser (n) | Passer (p) : ").lower().strip()

    if choice == "o":
        validated.append(memory)
    elif choice == "n":
        rejected.append(memory)
    else:
        skipped.append(memory)
        print("Mémoire mise de côté.")

# ======================
# TRAITEMENT
# ======================

existing_memories = get_existing_memories()

added_count     = 0
updated_count   = 0
duplicate_count = 0
category_counts = {}

for memory in validated:
    result = reconcile_local(memory, existing_memories)
    classification = result["classification"]
    match          = result["match"]
    score          = result["score"]

    print(f"\n→ {memory}")
    print(f"  Classification : {classification}  (similarité : {score:.2f})")

    if classification == "DOUBLON":
        print(f"  Doublon de : {match['memory']}")
        duplicate_count += 1
        continue

    if classification == "UPDATE":
        print(f"\n  Ancienne mémoire : {match['memory']}")
        print(f"  Fichier          : {match['file']}")
        confirm = input("  Remplacer ? (o/n) : ").lower().strip()

        if confirm == "o":
            new_text = input("  Nouvelle version (Entrée = garder telle quelle) : ").strip()
            if not new_text:
                new_text = memory

            if update_memory_in_file(match["file"], match["memory"], new_text):
                updated_count += 1
                # mettre à jour la liste locale pour les comparaisons suivantes
                for m in existing_memories:
                    if m["memory"] == match["memory"]:
                        m["memory"] = new_text
                print("  Mémoire mise à jour.")
            else:
                print("  Mise à jour impossible.")
        else:
            print("  Mise à jour annulée.")
        continue

    # NEW
    category_file = detect_category(memory)
    outcome = add_memory_to_file(memory, category_file)

    if outcome == "added":
        added_count += 1
        category_counts[category_file] = category_counts.get(category_file, 0) + 1
        existing_memories.append({"file": category_file, "memory": memory})
    elif outcome == "duplicate":
        duplicate_count += 1

# ======================
# RÉSUMÉ
# ======================

print("\n===== RÉSUMÉ =====")
print(f"Acceptées      : {len(validated)}")
print(f"Nouvelles      : {added_count}")
print(f"Mises à jour   : {updated_count}")
print(f"Doublons       : {duplicate_count}")
print(f"Refusées       : {len(rejected)}")
print(f"Passées        : {len(skipped)}")
print(f"Appels API     : 0")

if category_counts:
    print("\nClassement :")
    for cat, count in category_counts.items():
        print(f"  - {cat} : {count}")

# ======================
# NETTOYAGE INBOX
# ======================

cleanup = input("\nVider l'Inbox ? (o/n) : ").lower().strip()

if cleanup == "o":
    inbox_path.write_text("# Mémoires à valider\n\nDate : À compléter\n\n", encoding="utf-8")
    print("Inbox vidée.")
else:
    print("Inbox conservée.")
