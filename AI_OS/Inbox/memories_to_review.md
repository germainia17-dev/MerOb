# Mémoires à valider

Date : 2026-06-04

## Haute confiance

- [ ] L'utilisateur s'appelle Germain Gibert et a 17 ans.
- [ ] Il est élève en 1ère STI2D au Lycée Joseph Fourier à Auxerre.
- [ ] Son projet phare pour le bac/STI2D est le développement d'une prothèse paralympique en impression 3D.
- [ ] Il développe un assistant IA en local, actuellement sur Raspberry Pi.
- [ ] Il utilise n8n et Claude Code pour l'automatisation.
- [ ] Il vise la certification Gemini for student.
- [ ] Il centralise sa gestion des connaissances dans un "second cerveau" nommé DigitBrain sur Obsidian.
- [ ] Il envisage d'acheter un MacBook Pro M4 Pro.
- [ ] Pour un MacBook Pro M4 Pro, il est conseillé de viser un modèle reconditionné certifié (environ 1 700 €) et d'éviter le M4 standard.
- [ ] Si le MacBook Pro M4 Pro est acheté, l'assistant IA local devra tourner dessus dans les deux semaines suivant la réception.
- [ ] L'utilisateur souhaite créer un outil pour résoudre le problème de la gestion des tokens avec Claude (notamment Claude Code).
- [ ] La gestion des tokens est un problème d'ingénierie logicielle (nettoyage et préparation), non d'intelligence artificielle.
- [ ] Les causes principales de la consommation excessive de tokens sont : l'envoi de fichiers inutiles (.git, node_modules, .venv, .trash Obsidian), l'absence de structure claire (fichiers de 2000 lignes) et l'absence de mémoire sélective.
- [ ] L'outil proposé pour la gestion des tokens est un script CLI en Python nommé `ContextOptimizer`.
- [ ] Le `ContextOptimizer` devra inclure trois fonctionnalités prioritaires :
    - [ ] **Smart Ignorer** : Scanner le dossier de projet et ignorer les fichiers binaires, dépendances et logs en utilisant la bibliothèque `pathspec` pour parser le `.gitignore`.
    - [ ] **Squelettisation du code** : Extraire uniquement le squelette (classes, définitions de fonctions, docstrings) des fichiers `.py` en utilisant le module `ast` de Python.
    - [ ] **Générateur de Prompt Contextuel** : Compiler les informations optimisées dans un fichier Markdown temporaire structuré pour Claude (arborescence, squelette des fichiers secondaires, code complet du fichier précis à traiter).

## À vérifier

- [ ] L'utilisateur est identifié comme souffrant du "syndrome de l'éparpillement" (lance beaucoup de projets - prothèse STI2D, assistant local sur Raspberry Pi, n8n, scripts Micro:bit, Adalo - sans forcément les terminer).
- [ ] Un événement majeur, VivaTech, est prévu dans moins de trois semaines (le 20 juin), et la question se pose de savoir si ses livrables (notamment le projet de prothèse) sont au niveau de l'ambition affichée.
- [ ] Le gaming sur Mac est un sujet bancal avec un catalogue macOS restrictif, et le MacBook Pro M4 Pro pourrait ne pas être adapté pour des jeux multijoueurs Windows (via couches de compatibilité).

## Faible priorité

- [ ] L'utilisateur est passionné de ski/snowboard (spot de prédilection aux Portes du Soleil).
- [ ] Ses jeux préférés sont Brawl Stars, Geometry Dash et GTA Online.
- [ ] Il consomme du French Rap / Cloud Rap (style Houdi).