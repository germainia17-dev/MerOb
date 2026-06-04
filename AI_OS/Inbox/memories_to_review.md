# Mémoires à valider

Date : 2026-06-04

## Haute confiance

- [ ] **Identité :**
    - Nom : Germain Gibert
    - Âge : 17 ans
    - Situation : Élève en 1ère STI2D au Lycée Joseph Fourier, Auxerre.
    - Profil physique : 1m77, mince.
- [ ] **Projets en cours :**
    - Développement d'une prothèse paralympique en impression 3D (projet majeur pour le bac/STI2D).
    - Assistant IA en local sur Raspberry Pi.
    - Gestion de connaissances : "DigitBrain" sous Obsidian.
    - Volonté de créer un outil pour optimiser la consommation de tokens sur Claude (notamment pour Claude Code, l'assistant local et la prothèse 3D).
- [ ] **Objectifs :**
    - Vise la certification Gemini for student.
    - Participer/performer à l'événement VivaTech (prévu autour du 20 juin).
    - Acheter un MacBook Pro M4 Pro pour améliorer ses capacités de développement IA et 3D.
    - Investir dans un outil durable pour ses futures études supérieures (école d'ingé, info).
- [ ] **Préférences de travail & Tendances :**
    - Met les mains dans la tech.
    - Tendance à l'éparpillement, lançant de nombreux projets (prothèse STI2D, assistant local Raspberry Pi, n8n, scripts Micro:bit, Adalo) sans toujours les terminer.
    - Tendance à chercher des solutions IA pour des problèmes qui relèvent de l'ingénierie logicielle (ex: gestion des tokens).
    - Habitudes actuelles menant à une surconsommation de tokens avec Claude : envoi de fichiers inutiles (.git, node_modules, .venv, .trash Obsidian), absence de structure claire (fichiers de 2000 lignes), absence de mémoire sélective (redonner tout l'historique).
    - Intérêt pour le gaming compétitif (Brawl Stars, Geometry Dash, GTA Online), mais le gaming sur Mac est restrictif pour ses jeux.
- [ ] **Outils utilisés :**
    - Raspberry Pi (pour assistant IA local).
    - n8n (pour l'automatisation).
    - Claude Code (pour l'IA).
    - Obsidian (pour le "second cerveau" DigitBrain).
    - Micro:bit, Adalo (mentionnés dans les projets potentiellement éparpillés).
- [ ] **Connaissances durables :**
    - Centres d'intérêt : Ski/snowboard (spot de prédilection : Portes du Soleil - Avoriaz/Morzine), gaming (Brawl Stars, Geometry Dash, GTA Online), French Rap / Cloud Rap (style Houdi).
    - Style : Coupe buzz cut / textured crop.
    - La gestion de la taille du contexte pour les LLM est un problème d'ingénierie logicielle (tri, filtrage, parsing), pas un problème d'intelligence artificielle.
- [ ] **Décisions importantes :**
    - Désire acheter un MacBook Pro M4 Pro.
    - **Si achat du MacBook M4 Pro :**
        - Doit privilégier le modèle "Pro" (non basique M4) pour la performance IA et le développement lourd (minimum 24 Go de RAM, bande passante M4 Pro).
        - Doit viser le reconditionné certifié (BackMarket, Refurb Apple, Fnac Occasion ou Okamac) pour économiser environ 600 €.
- [ ] **Tâches utiles :**
    - **Si achat du MacBook Pro M4 Pro :** Faire en sorte que l'assistant IA local tourne dessus dans les deux semaines suivant la réception de l'appareil.
    - **Pour l'outil d'optimisation des tokens sur Claude (nommé "ContextOptimizer") :**
        - **Commencer AUJOURD'HUI par un script Python CLI simple qui :**
            - Prend un chemin de dossier.
            - Lit le `.gitignore` du projet.
            - Concatène le texte des fichiers restants dans un seul fichier `context.txt` en utilisant des balises XML (`<file name="main.py"> [code] </file>`).
            - Affiche le compte exact de tokens (utiliser la bibliothèque `tiktoken` ou `anthropic`).
        - **Architecture envisagée pour l'outil (après le script simple) :**
            - **Étape 1 : Le "Smart Ignorer" :** Utiliser la bibliothèque `pathspec` en Python pour parser le `.gitignore` et exclure automatiquement les fichiers binaires, dépendances et logs.
            - **Étape 2 : La "Squelettisation" du code :** Utiliser le module `ast` (Abstract Syntax Tree) de Python pour lire les fichiers `.py` et en extraire uniquement le squelette (nom des classes, définitions des fonctions et docstrings) afin de diviser la consommation de tokens par 10.
            - **Étape 3 : Le Générateur de Prompt Contextuel :** Compiler les informations optimisées (arborescence du projet, squelette des fichiers secondaires, code complet du fichier précis sur lequel Claude doit travailler) dans un seul fichier Markdown temporaire.

## À vérifier

- [ ] ...

## Faible priorité

- [ ] ...