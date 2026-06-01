from pathlib import Path
from dotenv import load_dotenv
from google import genai
import os

# ======================
# CONFIG
# ======================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Erreur : GEMINI_API_KEY manquante dans le fichier .env")

client = genai.Client(api_key=api_key)

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
    existing_memories = []

    for file in memory_dir.glob("*.md"):
        file_content = file.read_text(encoding="utf-8")

        for line in file_content.splitlines():
            if line.startswith("- "):
                memory = line.replace("- ", "").strip()

                if memory:
                    existing_memories.append(
                        {
                            "file": file.name,
                            "memory": memory,
                        }
                    )

    return existing_memories


def detect_category(memory):
    text = memory.lower()

    if (
        "a décidé" in text
        or "decision" in text
        or "décision" in text
        or "choix" in text
        or "a choisi" in text
        or "validation" in text
        or "valider" in text
        or "intégration" in text
        or "integration" in text
    ):
        return "Decisions.md"

    if (
        "idée" in text
        or "idee" in text
        or "ajouter" in text
        or "fonctionnalité" in text
        or "fonctionnalite" in text
        or "compteur" in text
        or "piste" in text
    ):
        return "Ideas.md"

    if (
        "a appris" in text
        or "comprend" in text
        or "connaît" in text
        or "connait" in text
        or "sait" in text
        or "concept" in text
        or "rag" in text
        or "embedding" in text
    ):
        return "Knowledge.md"

    if (
        "doit faire" in text
        or "à faire" in text
        or "a faire" in text
        or "tâche" in text
        or "tache" in text
        or "todo" in text
        or "corriger" in text
        or "tester" in text
        or "créer" in text
        or "creer" in text
    ):
        return "Tasks.md"

    if (
        "projet" in text
        or "développe" in text
        or "developpe" in text
        or "ai os" in text
    ):
        return "Projects.md"

    if (
        "obsidian" in text
        or "gemini" in text
        or "claude" in text
        or "chatgpt" in text
        or "outil" in text
        or "python" in text
        or "vscode" in text
        or "vs code" in text
    ):
        return "Tools.md"

    if (
        "macbook" in text
        or "mac " in text
        or "ordinateur" in text
        or "utilisateur travaille" in text
        or "utilisateur utilise un mac" in text
    ):
        return "Identity.md"

    if (
        "objectif" in text
        or "veut" in text
        or "souhaite" in text
        or "but" in text
        or "l'objectif" in text
    ):
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
        return "duplicate"

    existing += f"- {memory}\n"
    file_path.write_text(existing, encoding="utf-8")

    return "added"


def update_memory_in_file(filename, old_memory, new_memory):
    file_path = memory_dir / filename

    if not file_path.exists():
        print(f"Erreur : fichier introuvable : {filename}")
        return False

    content = file_path.read_text(encoding="utf-8")

    old_line = f"- {old_memory}"
    new_line = f"- {new_memory}"

    if old_line not in content:
        print("Erreur : ancienne mémoire introuvable dans le fichier.")
        return False

    content = content.replace(old_line, new_line)
    file_path.write_text(content, encoding="utf-8")

    return True


def reconcile_with_gemini(new_memory):
    existing_memories = get_existing_memories()

    if not existing_memories:
        return {
            "classification": "NEW",
            "file": None,
            "old": None,
            "current": None,
            "new": new_memory,
            "raw": "",
        }

    memories_text = ""

    for index, item in enumerate(existing_memories, start=1):
        memories_text += f"{index}. [{item['file']}] {item['memory']}\n"

    prompt = f"""
Tu es un système de mémoire.

Compare la mémoire candidate avec les mémoires existantes.

Tu dois répondre avec UNE SEULE classification :

DOUBLON :
La mémoire candidate répète une information déjà présente.

UPDATE :
La mémoire candidate remplace une mémoire existante plus ancienne.

OLD_INFO :
La mémoire candidate est une ancienne information déjà remplacée par une mémoire plus récente.
Exemple :
Mémoire existante : L'utilisateur travaille sur un Mac M4.
Mémoire candidate : L'utilisateur travaille sur un MacBook Air M1.
=> OLD_INFO

NEW :
La mémoire candidate ajoute une information réellement nouvelle.

Réponds UNIQUEMENT dans ce format :

Classification: DOUBLON

ou

Classification: UPDATE
File: nom_du_fichier.md
Old: ancienne mémoire à remplacer
New: nouvelle mémoire reformulée

ou

Classification: OLD_INFO
File: nom_du_fichier.md
Old: mémoire candidate obsolète
Current: mémoire actuelle plus récente

ou

Classification: NEW
New: mémoire reformulée

Règles :
- Si la candidate est plus récente et remplace une ancienne info, réponds UPDATE.
- Si la candidate est plus ancienne que l'info existante, réponds OLD_INFO.
- Si elle répète une info existante, réponds DOUBLON.
- Si elle ajoute une vraie nouvelle info, réponds NEW.
- Ne mets aucune explication.
- Respecte exactement les labels : Classification, File, Old, Current, New.

Mémoires existantes :

{memories_text}

Mémoire candidate :

{new_memory}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    result = response.text.strip()

    classification = None
    target_file = None
    old_memory = None
    current_memory = None
    new_memory_text = new_memory

    for line in result.splitlines():
        line = line.strip()

        if line.startswith("Classification:"):
            classification = line.replace("Classification:", "").strip()

        elif line.startswith("File:"):
            target_file = line.replace("File:", "").strip()

        elif line.startswith("Old:"):
            old_memory = line.replace("Old:", "").strip()

        elif line.startswith("Current:"):
            current_memory = line.replace("Current:", "").strip()

        elif line.startswith("New:"):
            new_memory_text = line.replace("New:", "").strip()

    if not classification:
        classification = "NEW"

    return {
        "classification": classification,
        "file": target_file,
        "old": old_memory,
        "current": current_memory,
        "new": new_memory_text,
        "raw": result,
    }


# ======================
# VALIDATION
# ======================

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

# ======================
# TRAITEMENT
# ======================

added_count = 0
updated_count = 0
duplicate_count = 0
old_info_count = 0
category_counts = {}

for memory in validated:
    print(f"\nAnalyse mémoire : {memory}")

    reconciliation = reconcile_with_gemini(memory)

    classification = reconciliation["classification"]
    target_file = reconciliation["file"]
    old_memory = reconciliation["old"]
    current_memory = reconciliation["current"]
    final_memory = reconciliation["new"]

    if classification == "DOUBLON":
        duplicate_count += 1
        print("Doublon détecté, ignoré.")
        continue

    if classification == "OLD_INFO":
        old_info_count += 1
        print("Ancienne information obsolète détectée, ignorée.")

        if current_memory:
            print(f"Mémoire actuelle conservée : {current_memory}")

        continue

    if classification == "UPDATE" and target_file and old_memory and final_memory:
        print("\n===== UPDATE DÉTECTÉ =====")
        print("Ancienne mémoire :")
        print(old_memory)
        print("\nNouvelle mémoire :")
        print(final_memory)

        confirm = input("\nRemplacer ? (o/n) : ").lower().strip()

        if confirm == "o":
            success = update_memory_in_file(target_file, old_memory, final_memory)

            if success:
                updated_count += 1
                print("Mémoire mise à jour.")
            else:
                print("Mise à jour impossible.")

        else:
            print("Mise à jour annulée.")

        continue

    category_file = detect_category(final_memory)
    result = add_memory_to_file(final_memory, category_file)

    if result == "added":
        added_count += 1
        category_counts[category_file] = category_counts.get(category_file, 0) + 1

    elif result == "duplicate":
        duplicate_count += 1

# ======================
# RÉSUMÉ
# ======================

print("\n===== RÉSUMÉ =====")
print(f"Acceptées par toi : {len(validated)}")
print(f"Nouvelles ajoutées : {added_count}")
print(f"Mises à jour : {updated_count}")
print(f"Doublons ignorés : {duplicate_count}")
print(f"Anciennes infos ignorées : {old_info_count}")
print(f"Refusées : {len(rejected)}")
print(f"Passées : {len(skipped)}")

if category_counts:
    print("\nClassement :")
    for category, count in category_counts.items():
        print(f"- {category} : {count}")

print(f"\nDossier mémoire : {memory_dir}")

# ======================
# NETTOYAGE INBOX
# ======================

cleanup = input(
    "\nVider l'Inbox maintenant ? (o/n) : "
).lower().strip()

if cleanup == "o":

    inbox_content = f"""# Mémoires à valider

Date : À compléter

"""

    inbox_path.write_text(
        inbox_content,
        encoding="utf-8"
    )

    print("Inbox vidée.")

else:

    print("Inbox conservée.")
