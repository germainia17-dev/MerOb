# Installation

De zéro à fonctionnel en ~5 minutes.

## Prérequis

- **Python 3.10+** ([télécharger](https://www.python.org/downloads/))
- **Obsidian** avec au moins un vault ouvert
- Un navigateur **Chrome / Edge / Brave**
- Une **clé API Gemini** (gratuite : https://aistudio.google.com/apikey)

## 1. Lancer le serveur

```bash
git clone <url-du-repo>
cd ai-os

# macOS / Linux
./start.sh

# Windows
start.bat
```

Au premier lancement, le script :
1. crée l'environnement Python et installe les dépendances,
2. **détecte automatiquement ton vault Obsidian** (ou te demande le chemin),
3. te demande ta **clé Gemini** (stockée dans `.env`),
4. démarre le serveur sur http://localhost:8000.

Laisse cette fenêtre ouverte. Vérifie que ça tourne :
👉 http://localhost:8000/health doit répondre `{"status":"ok", ...}`.

> Pas de `start.sh` ? Équivalent manuel :
> ```bash
> python3 -m venv venv && source venv/bin/activate
> pip install --upgrade pip && pip install -r requirements.txt
> python run.py
> ```

## 2. Installer l'extension navigateur

1. Ouvre `chrome://extensions`
2. Active le **Mode développeur** (en haut à droite)
3. Clique **Charger l'extension non empaquetée**
4. Sélectionne le dossier `chrome_extension/`
5. Va sur ChatGPT, Claude ou Gemini → le panneau 🧠 apparaît en bas à droite

## 3. Utiliser

- **Capturer** : en fin de conversation, clique **⬆ Extraire**. Les mémoires
  sont rangées automatiquement dans ton vault Obsidian (`Memories/` + `Categories/`).
- **Réinjecter** : tape ton message — les mémoires pertinentes remontent dans le
  panneau. Clique **⬇ Injecter** pour les coller dans le prompt.

## Dépannage

| Symptôme | Solution |
|---|---|
| `Python 3.10+ requis` | Installe une version récente de Python |
| Le panneau dit « Serveur inaccessible » | Le serveur n'est pas lancé → relance `./start.sh` |
| « Clé API Gemini manquante » | Lance `python config.py` ou édite `.env` |
| Mauvais vault détecté | Édite `config.json` (clé `"vault"`) avec le bon chemin |
| Aucune mémoire trouvée | Vérifie `http://localhost:8000/health` → champ `vault` |
