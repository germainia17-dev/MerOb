from pathlib import Path
from difflib import SequenceMatcher

memory_dir = Path("AI_OS/Memory")

if not memory_dir.exists():
    print("Aucune mémoire trouvée.")
    exit()

all_memories = []

for file in memory_dir.glob("*.md"):
    content = file.read_text(encoding="utf-8")

    for line in content.splitlines():
        if line.startswith("- "):
            memory = line.replace("- ", "").strip()

            if memory:
                all_memories.append(
                    {
                        "file": file.name,
                        "memory": memory
                    }
                )

print("\n===== TEST DE RÉCONCILIATION =====\n")

new_memory = input("Nouvelle mémoire : ").strip()

if not new_memory:
    print("Aucune mémoire saisie.")
    exit()

best_match = None
best_score = 0

for item in all_memories:

    score = SequenceMatcher(
        None,
        new_memory.lower(),
        item["memory"].lower()
    ).ratio()

    if score > best_score:
        best_score = score
        best_match = item

print("\n===== RÉSULTAT =====\n")

if best_score > 0.90:

    print("Type : DOUBLON")
    print(f"Confiance : {best_score:.2f}")
    print(f"Fichier : {best_match['file']}")
    print(f"Mémoire existante :")
    print(best_match["memory"])

elif best_score > 0.60:

    print("Type : POSSIBLE MISE À JOUR")
    print(f"Confiance : {best_score:.2f}")
    print(f"Fichier : {best_match['file']}")

    print("\nMémoire existante :")
    print(best_match["memory"])

    print("\nNouvelle mémoire :")
    print(new_memory)

else:

    print("Type : NOUVELLE INFORMATION")
    print(f"Confiance : {best_score:.2f}")

    print("\nAucune mémoire proche trouvée.")