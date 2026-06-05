@echo off
REM AI OS - demarrage en une commande (Windows)
REM   start.bat
cd /d "%~dp0"

REM Garde-fou : Python 3.10+ requis
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>nul
if errorlevel 1 (
  echo AI OS requiert Python 3.10+.
  echo Installe une version recente depuis https://www.python.org/downloads/
  exit /b 1
)

if not exist venv (
  echo Creation de l'environnement Python...
  python -m venv venv
)

call venv\Scripts\activate

echo Mise a jour de pip...
pip install -q --upgrade pip

echo Installation des dependances...
pip install -q -r requirements.txt

echo Lancement d'AI OS...
python run.py
