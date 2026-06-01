from pathlib import Path
from datetime import datetime
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

conversation_path = Path("conversation.txt")
inbox_path = Path("AI_OS/Inbox/memories_to_review.md")
architecture_path = Path("AI_OS/architecture_memory.md")

inbox_path.parent.mkdir(parents=True, exist_ok=True)

# ======================
# LECTURE DES FICHIERS
# ======================

if not conversation_path.exists():
    raise FileNotFoundError("Erreur : conversation.txt introuvable.")

conversation = conversation_path.read_text(encoding="utf-8")

architecture = ""

if architecture_path.exists():
    architecture = architecture_path.read_text(encoding="utf-8")

# ======================
# PROMPT GEMINI
# ======================

prompt = f"""
Tu es le module d'extraction mémoire de AI OS.

Ton rôle est d'analyser une conversation et d'extraire uniquement les informations réellement utiles à mémoriser.

Tu dois produire une note Markdown compatible avec Obsidian.

RÈGLE CRITIQUE :
Toutes les mémoires doivent être écrites comme des faits stables sur l'utilisateur, ses projets, ses décisions, ses outils ou ses objectifs.

Forme obligatoire :
- "L'utilisateur utilise..."
- "L'utilisateur développe..."
- "L'utilisateur veut..."
- "L'utilisateur a décidé..."
- "Le projet AI OS..."
- "L'objectif de l'utilisateur est..."

Formes interdites :
- "Utiliser..."
- "Développer..."
- "Créer..."
- "Continuer..."
- "Ajouter..."
- phrases à l'infinitif
- phrases sans sujet
- actions vagues

IMPORTANT :
- N'invente aucune information.
- Ne garde pas les phrases inutiles.
- Ne garde pas les remerciements.
- Ne garde pas les hésitations.
- Ne garde pas les répétitions.
- Ne crée jamais de section vide.
- Si une catégorie n'a aucune mémoire utile, ne l'affiche pas.
- Chaque mémoire doit être courte, claire, factuelle et exploitable.
- Chaque mémoire doit commencer par "- [ ]".
- Ne mets aucune explication hors Markdown.

Catégories autorisées :
- Identity
- Projects
- Goals
- Ideas
- Decisions
- Tools
- Knowledge
- Tasks
- Other

Règles de catégories :
- Identity : informations stables sur l'utilisateur, son environnement, son matériel, ses préférences durables.
- Projects : projets importants ou en cours.
- Goals : objectifs long terme ou moyen terme.
- Ideas : idées de fonctionnalités, produits, pistes futures.
- Decisions : décisions prises explicitement.
- Tools : outils utilisés, testés ou préférés.
- Knowledge : connaissances apprises ou concepts compris.
- Tasks : actions concrètes à faire.
- Other : seulement si aucune autre catégorie ne convient.

Format obligatoire :

# Mémoires à valider

Date : {datetime.now().strftime("%Y-%m-%d")}

## NomCategorie
- [ ] L'utilisateur ...

## AutreCategorie
- [ ] Le projet ...

Architecture mémoire du projet :
{architecture}

Conversation à analyser :
{conversation}
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
)

result = response.text.strip()

# ======================
# SAUVEGARDE
# ======================

inbox_path.write_text(result + "\n", encoding="utf-8")

print("Mémoire V2 générée ici : AI_OS/Inbox/memories_to_review.md")
