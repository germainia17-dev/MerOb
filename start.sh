#!/usr/bin/env bash
# Obsidian Chat Memory — one-command start (macOS / Linux)
#   ./start.sh
set -e
cd "$(dirname "$0")"

# Guard: Python 3.10+ required
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  echo "Obsidian Chat Memory requires Python 3.10+. Detected: $(python3 --version 2>&1)"
  echo "Download a recent version from https://www.python.org/downloads/"
  exit 1
fi

if [ ! -d venv ]; then
  echo "→ Creating Python environment…"
  python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

echo "→ Updating pip…"
pip install -q --upgrade pip

echo "→ Installing dependencies…"
pip install -q -r requirements.txt

echo "→ Starting Obsidian Chat Memory…"
python run.py
