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
    print(f"Obsidian Chat Memory requires Python 3.10 or newer (detected: {sys.version.split()[0]}).")
    print("Download a recent version from https://www.python.org/downloads/")
    sys.exit(1)

import config


def main():
    vault = config.resolve_vault()

    if vault is None:
        print("First run — let's set up your Obsidian vault.")
        vault = config.interactive_setup()
        if vault is None:
            print("\nSetup required to continue. Re-run: python run.py")
            return

    # Gemini key: needed for extraction (not for search/injection)
    if config.get_api_key() is None:
        config.setup_api_key()

    print(f"\n✓ Memory vault: {vault}")
    print("→ Obsidian Chat Memory server: http://localhost:8000")
    print("  (keep this window open; Ctrl+C to stop)\n")

    # Import tardif : uvicorn/server ne se chargent qu'une fois le vault prêt
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
