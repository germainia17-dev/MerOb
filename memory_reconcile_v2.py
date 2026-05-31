from pathlib import Path
from dotenv import load_dotenv
from google import genai
import os

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Erreur : GEMINI_API_KEY manquante dans le fichier .env")

client = genai.Client(api_key=api_key)

memory_dir = Path("AI_OS/Memory")

if not memory_dir.exists():
    print("Aucune mémoire trouvée.")
    exit()

existing_memories = []

for file in memory_dir.glob("*.md"):

    content = file.read_text(encoding="utf-8")

    for line in content.splitlines():

        if line.startswith("- "):

            memory = line.replace("- ", "").strip()

            if memory:

                existing_memories.append(
                    {
                        "file": file.name,
                        "memory": memory
                    }
                )

print("\n===== RÉCONCILIATION IA =====\n")

new_memory = input("Nouvelle mémoire : ").strip()

if not new_memory:
    print("Aucune mémoire saisie.")
    exit()

memories_text = ""

for index, item in enumerate(existing_memories, start=1):

    memories_text += (
        f"{index}. "
        f"[{item['file']}] "
        f"{item['memory']}\n"
    )

prompt = f"""
Tu es un système de mémoire.

Compare la nouvelle mémoire avec les mémoires existantes.

Réponds UNIQUEMENT dans ce format :

Classification: DOUBLON

ou

Classification: UPDATE
File: nom_du_fichier.md
Old: ancienne mémoire
New: nouvelle mémoire reformulée

ou

Classification: NEW

Mémoires existantes :

{memories_text}

Nouvelle mémoire :

{new_memory}
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
)

result = response.text.strip()

print("\n===== ANALYSE =====\n")
print(result)

# ----------------------
# UPDATE
# ----------------------

if "Classification: UPDATE" in result:

    lines = result.splitlines()

    target_file = None
    old_memory = None
    new_memory_text = None

    for line in lines:

        if line.startswith("File:"):
            target_file = line.replace("File:", "").strip()

        elif line.startswith("Old:"):
            old_memory = line.replace("Old:", "").strip()

        elif line.startswith("New:"):
            new_memory_text = line.replace("New:", "").strip()

    if (
        target_file
        and old_memory
        and new_memory_text
    ):

        print("\n===== UPDATE DÉTECTÉ =====\n")

        print("Ancienne mémoire :")
        print(old_memory)

        print("\nNouvelle mémoire :")
        print(new_memory_text)

        confirm = input(
            "\nRemplacer ? (o/n) : "
        ).lower().strip()

        if confirm == "o":

            file_path = memory_dir / target_file

            content = file_path.read_text(
                encoding="utf-8"
            )

            content = content.replace(
                f"- {old_memory}",
                f"- {new_memory_text}"
            )

            file_path.write_text(
                content,
                encoding="utf-8"
            )

            print("\nMémoire mise à jour.")

        else:

            print("\nMise à jour annulée.")

# ----------------------
# NEW
# ----------------------

elif "Classification: NEW" in result:

    print(
        "\nNouvelle information détectée."
    )

# ----------------------
# DOUBLON
# ----------------------

elif "Classification: DOUBLON" in result:

    print(
        "\nDoublon détecté."
    )