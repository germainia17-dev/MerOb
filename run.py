"""
run.py
──────
Point d'entrée unique d'Obsidian Chat Memory (macOS / Windows / Linux).

  python run.py

  1. Au premier lancement, configure le vault Obsidian (auto-détection
     ou saisie manuelle), puis le mémorise dans config.json.
  2. Démarre le serveur local sur http://localhost:8000

Plus besoin de launchd : un simple `python run.py` suffit sur tous les OS.
"""

import sys

if sys.version_info < (3, 10):
    print(f"Obsidian Chat Memory requiert Python 3.10 ou plus récent (détecté : {sys.version.split()[0]}).")
    print("Installe une version récente depuis https://www.python.org/downloads/")
    sys.exit(1)

import config


def main():
    vault = config.resolve_vault()

    if vault is None:
        print("Premier lancement — configurons ton vault Obsidian.")
        vault = config.interactive_setup()
        if vault is None:
            print("\nConfiguration nécessaire pour continuer. Relance : python run.py")
            return

    # Clé Gemini : nécessaire pour l'extraction (pas pour la recherche/réinjection)
    if config.get_api_key() is None:
        config.setup_api_key()

    print(f"\n✓ Vault des mémoires : {vault}")
    print("→ Serveur Obsidian Chat Memory : http://localhost:8000")
    print("  (garde cette fenêtre ouverte ; Ctrl+C pour arrêter)\n")

    # Import tardif : uvicorn/server ne se chargent qu'une fois le vault prêt
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
