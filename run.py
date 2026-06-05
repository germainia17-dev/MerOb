"""
run.py
──────
Single entry point for Obsidian Chat Memory (macOS / Windows / Linux).

  python run.py

  1. On first launch, configures the Obsidian vault (auto-detection
     or manual input), then remembers it in config.json.
  2. Starts the local server on http://localhost:8000

No more launchd: a simple `python run.py` works on every OS.
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

    # Late import: uvicorn/server only load once the vault is ready
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
