#!/usr/bin/env bash
# AI OS — démarrage en une commande (macOS / Linux)
#   ./start.sh
set -e
cd "$(dirname "$0")"

if [ ! -d venv ]; then
  echo "→ Création de l'environnement Python…"
  python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

echo "→ Installation des dépendances…"
pip install -q -r requirements.txt

echo "→ Lancement d'AI OS…"
python run.py
