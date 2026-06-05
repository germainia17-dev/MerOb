"""
config.py
─────────
Resolves where to write the memories (the Obsidian folder).

Resolution order (highest to lowest priority):
  1. Environment variable      OBSIDIAN_VAULT
  2. Local file                config.json  ("vault" key)
  3. Auto-detection            via obsidian.json (list of Obsidian vaults)
  4. Interactive setup         (first launch)

Goal: a stranger can clone the repo and have it work without touching
the code. The path is NEVER hardcoded.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"


# ======================
# OBSIDIAN LOCATION
# ======================

def _obsidian_config_path() -> Path:
    """Path to obsidian.json depending on the OS."""
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library/Application Support/obsidian/obsidian.json"
    if sys.platform.startswith("win"):
        return Path(os.getenv("APPDATA", home)) / "obsidian/obsidian.json"
    return home / ".config/obsidian/obsidian.json"


def detect_obsidian_vaults() -> list:
    """Lists known Obsidian vaults, the open / most recent one first."""
    p = _obsidian_config_path()
    if not p.exists():
        return []
    try:
        data   = json.loads(p.read_text(encoding="utf-8"))
        vaults = data.get("vaults", {})
    except Exception:
        return []

    items = []
    for info in vaults.values():
        path = info.get("path")
        if path and Path(path).exists():
            items.append((Path(path), bool(info.get("open")), info.get("ts", 0)))

    # open vault first, then most recently used
    items.sort(key=lambda x: (not x[1], -x[2]))
    return [i[0] for i in items]


# ======================
# LOCAL CONFIG FILE
# ======================

def load_saved_vault() -> Path | None:
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            v = data.get("vault")
            if v and Path(v).exists():
                return Path(v)
        except Exception:
            pass
    return None


def save_vault(path: Path) -> None:
    data = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["vault"] = str(path)
    CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ======================
# RESOLUTION
# ======================

def resolve_vault() -> Path | None:
    """Resolves the memory folder without interaction. None if not found."""
    env = os.getenv("OBSIDIAN_VAULT")
    if env and Path(env).exists():
        return Path(env)

    saved = load_saved_vault()
    if saved:
        return saved

    vaults = detect_obsidian_vaults()
    if vaults:
        # a single vault detected → remember it for next time
        if len(vaults) == 1:
            save_vault(vaults[0])
        return vaults[0]

    return None


def interactive_setup() -> Path | None:
    """First-run interactive vault configuration (call from a terminal)."""
    print("\n=== Obsidian Chat Memory — Vault Setup ===\n")
    vaults = detect_obsidian_vaults()

    if vaults:
        print("Obsidian vaults detected:")
        for i, v in enumerate(vaults, 1):
            print(f"  {i}. {v}")
        print(f"  {len(vaults) + 1}. Other (enter path manually)")
        choice = input("\nChoice: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(vaults):
            chosen = vaults[int(choice) - 1]
            save_vault(chosen)
            print(f"\n✓ Vault saved: {chosen}")
            return chosen

    manual = input("Paste the full path to your Obsidian vault: ").strip().strip('"')
    if manual and Path(manual).exists():
        chosen = Path(manual)
        save_vault(chosen)
        print(f"\n✓ Vault saved: {chosen}")
        return chosen

    print("\n⚠ Invalid path. Setup cancelled.")
    return None


# Shared error message when no vault is resolved
NO_VAULT_MSG = (
    "No Obsidian vault configured.\n"
    "  → Run setup:  python config.py\n"
    "  → or set:     export OBSIDIAN_VAULT=\"/path/to/your/vault\""
)


# ======================
# GEMINI API KEY (.env)
# ======================

ENV_FILE = Path(__file__).parent / ".env"


def get_api_key() -> str | None:
    """Reads GEMINI_API_KEY from .env (or the environment)."""
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY")


def save_api_key(key: str) -> None:
    """Writes / updates GEMINI_API_KEY in .env."""
    lines, found = [], False
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("GEMINI_API_KEY"):
                lines.append(f"GEMINI_API_KEY={key}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"GEMINI_API_KEY={key}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def setup_api_key() -> str | None:
    """Interactive Gemini API key setup."""
    print("\n=== Gemini API Key (required for memory extraction) ===")
    print("Free in 30 seconds: https://aistudio.google.com/apikey")
    key = input("Paste your Gemini key (Enter to configure later): ").strip()
    if not key:
        print("→ You can add it later by editing the .env file")
        return None
    save_api_key(key)
    print("✓ Key saved to .env")
    return key


NO_API_KEY_MSG = (
    "Gemini API key missing (required for extraction).\n"
    "  → Get one for free: https://aistudio.google.com/apikey\n"
    "  → Then run:  python config.py   (or add GEMINI_API_KEY=... to .env)"
)


if __name__ == "__main__":
    interactive_setup()
    setup_api_key()
