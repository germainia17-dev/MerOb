from pathlib import Path

# Fichiers
inbox_path = Path("AI_OS/Inbox/memories_to_review.md")
memory_dir = Path("AI_OS/Memory")

# Création du dossier Memory si nécessaire
memory_dir.mkdir(parents=True, exist_ok=True)

# Vérification que l'inbox existe
if not inbox_path.exists():
    print("Erreur : aucun fichier de mémoires à valider trouvé.")
    exit()

# Lecture des mémoires candidates
content = inbox_path.read_text(encoding="utf-8")

lines = content.splitlines()
memories = []

for line in lines:
    if line.startswith("- [ ] "):
        memory = line.replace("- [ ] ", "").strip()

        if memory:
            memories.append(memory)

if not memories:
    print("Aucune mémoire à valider.")
    exit()

validated = []
rejected = []
skipped = []

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


def detect_category(memory):
    text = memory.lower()

    if "projet" in text or "développe" in text or "developpe" in text or "ai os" in text:
        return "Projects.md"

    if "obsidian" in text or "gemini" in text or "claude" in text or "chatgpt" in text or "outil" in text:
        return "Tools.md"

    if "macbook" in text or "utilisateur travaille" in text or "ordinateur" in text:
        return "Identity.md"

    if "objectif" in text or "veut" in text or "souhaite" in text or "but" in text:
        return "Goals.md"

    return "Other.md"


def add_memory_to_file(memory, filename):
    file_path = memory_dir / filename

    title = filename.replace(".md", "")
    existing = ""

    if file_path.exists():
        existing = file_path.read_text(encoding="utf-8")

    if not existing:
        existing = f"# {title}\n\n"

    if memory in existing:
        print(f"Déjà existante, ignorée : {memory}")
        return False, True

    existing += f"- {memory}\n"
    file_path.write_text(existing, encoding="utf-8")

    return True, False


added_count = 0
duplicate_count = 0
category_counts = {}

for memory in validated:
    category_file = detect_category(memory)
    added, duplicate = add_memory_to_file(memory, category_file)

    if added:
        added_count += 1
        category_counts[category_file] = category_counts.get(category_file, 0) + 1

    if duplicate:
        duplicate_count += 1

print("\n===== RÉSUMÉ =====")
print(f"Acceptées par toi : {len(validated)}")
print(f"Nouvelles ajoutées : {added_count}")
print(f"Doublons ignorés : {duplicate_count}")
print(f"Refusées : {len(rejected)}")
print(f"Passées : {len(skipped)}")

if category_counts:
    print("\nClassement :")
    for category, count in category_counts.items():
        print(f"- {category} : {count}")

print(f"\nDossier mémoire : {memory_dir}")
