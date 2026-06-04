"""
config.py
─────────
Résout l'emplacement où écrire les mémoires (dossier Obsidian).

Ordre de résolution (du plus prioritaire au moins prioritaire) :
  1. Variable d'environnement  OBSIDIAN_VAULT
  2. Fichier local             config.json  (clé "vault")
  3. Auto-détection            via obsidian.json (liste des vaults Obsidian)
  4. Configuration interactive (premier lancement)

Objectif : qu'un inconnu puisse cloner le repo et que ça marche sans
toucher au code. Le chemin n'est JAMAIS codé en dur.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"


# ======================
# EMPLACEMENT D'OBSIDIAN
# ======================

def _obsidian_config_path() -> Path:
    """Chemin du obsidian.json selon l'OS."""
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library/Application Support/obsidian/obsidian.json"
    if sys.platform.startswith("win"):
        return Path(os.getenv("APPDATA", home)) / "obsidian/obsidian.json"
    return home / ".config/obsidian/obsidian.json"


def detect_obsidian_vaults() -> list:
    """Liste les vaults Obsidian connus, le vault ouvert / le plus récent d'abord."""
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

    # vault ouvert en premier, puis le plus récemment utilisé
    items.sort(key=lambda x: (not x[1], -x[2]))
    return [i[0] for i in items]


# ======================
# FICHIER DE CONFIG LOCAL
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
# RÉSOLUTION
# ======================

def resolve_vault() -> Path | None:
    """Résout le dossier des mémoires sans interaction. None si introuvable."""
    env = os.getenv("OBSIDIAN_VAULT")
    if env and Path(env).exists():
        return Path(env)

    saved = load_saved_vault()
    if saved:
        return saved

    vaults = detect_obsidian_vaults()
    if vaults:
        # un seul vault détecté → on le mémorise pour les fois suivantes
        if len(vaults) == 1:
            save_vault(vaults[0])
        return vaults[0]

    return None


def interactive_setup() -> Path | None:
    """Configuration au premier lancement (à appeler depuis un terminal)."""
    print("\n=== Configuration AI OS — dossier Obsidian ===\n")
    vaults = detect_obsidian_vaults()

    if vaults:
        print("Vaults Obsidian détectés :")
        for i, v in enumerate(vaults, 1):
            print(f"  {i}. {v}")
        print(f"  {len(vaults) + 1}. Autre (saisir un chemin manuellement)")
        choice = input("\nChoix : ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(vaults):
            chosen = vaults[int(choice) - 1]
            save_vault(chosen)
            print(f"\n✓ Vault enregistré : {chosen}")
            return chosen

    manual = input("Colle le chemin complet de ton vault Obsidian : ").strip().strip('"')
    if manual and Path(manual).exists():
        chosen = Path(manual)
        save_vault(chosen)
        print(f"\n✓ Vault enregistré : {chosen}")
        return chosen

    print("\n⚠ Chemin invalide. Configuration annulée.")
    return None


# Message d'erreur partagé quand aucun vault n'est résolu
NO_VAULT_MSG = (
    "Aucun vault Obsidian configuré.\n"
    "  → Lance la configuration :  python config.py\n"
    "  → ou définis la variable :  export OBSIDIAN_VAULT=\"/chemin/vers/ton/vault\""
)


if __name__ == "__main__":
    interactive_setup()
