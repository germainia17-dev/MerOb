#!/usr/bin/env bash
# AI OS — démarrage en une commande (macOS / Linux)
#   ./start.sh
set -e
cd "$(dirname "$0")"

# Garde-fou : Python 3.10+ requis
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  echo "AI OS requiert Python 3.10+. Version détectée : $(python3 --version 2>&1)"
  echo "Installe une version récente depuis https://www.python.org/downloads/"
  exit 1
fi

if [ ! -d venv ]; then
  echo "→ Création de l'environnement Python…"
  python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

echo "→ Mise à jour de pip…"
pip install -q --upgrade pip

echo "→ Installation des dépendances…"
pip install -q -r requirements.txt

echo "→ Lancement d'AI OS…"
python run.py
