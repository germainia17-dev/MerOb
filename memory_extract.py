from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from google import genai
import os

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Erreur : GEMINI_API_KEY manquante dans le fichier .env")

client = genai.Client(api_key=api_key)

conversation_path = Path("conversation.txt")
inbox_path = Path("AI_OS/Inbox/memories_to_review.md")

inbox_path.parent.mkdir(parents=True, exist_ok=True)

conversation = conversation_path.read_text(encoding="utf-8")

prompt = f"""
Tu es le module mémoire d'un assistant IA personnel.

Analyse cette conversation et extrais uniquement les informations importantes à mémoriser.

À garder :
- projets de l'utilisateur
- objectifs
- préférences de travail
- outils utilisés
- décisions importantes
- connaissances durables
- tâches utiles

À ignorer :
- phrases inutiles
- remerciements
- hésitations
- répétitions
- détails temporaires sans intérêt

Retourne uniquement du Markdown propre pour Obsidian.

Format obligatoire :

# Mémoires à valider

Date : {datetime.now().strftime("%Y-%m-%d")}

## Haute confiance

- [ ] ...

## À vérifier

- [ ] ...

## Faible priorité

- [ ] ...

Conversation :
{conversation}
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
)

result = response.text

inbox_path.write_text(result, encoding="utf-8")

print("Mémoire générée ici : AI_OS/Inbox/memories_to_review.md")
