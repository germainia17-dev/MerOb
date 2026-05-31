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
                existing_memories.append({
                    "file": file.name,
                    "memory": memory
                })

if not existing_memories:
    print("Aucune mémoire existante à comparer.")
    exit()

print("\n===== RÉCONCILIATION IA =====\n")

new_memory = input("Nouvelle mémoire : ").strip()

if not new_memory:
    print("Aucune mémoire saisie.")
    exit()

memories_text = ""

for index, item in enumerate(existing_memories, start=1):
    memories_text += f"{index}. [{item['file']}] {item['memory']}\n"

prompt = f"""
Tu es le module de réconciliation mémoire d'un assistant IA personnel.

Ton rôle est de comparer une nouvelle mémoire avec les mémoires existantes.

Tu dois déterminer si la nouvelle mémoire est :
- DOUBLON : elle répète une information déjà présente.
- UPDATE : elle remplace ou met à jour une ancienne information.
- CONTRADICTION : elle contredit une ancienne information sans clairement la remplacer.
- NEW : elle ajoute une information nouvelle.

Réponds uniquement avec ce format :

Classification : DOUBLON / UPDATE / CONTRADICTION / NEW
Fichier concerné : nom_du_fichier.md ou Aucun
Mémoire existante concernée : texte exact ou Aucune
Nouvelle mémoire reformulée : phrase claire
Raison : explication courte

Mémoires existantes :
{memories_text}

Nouvelle mémoire :
{new_memory}
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
)

print("\n===== RÉSULTAT IA =====\n")
print(response.text)