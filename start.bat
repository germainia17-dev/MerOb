@echo off
REM AI OS - demarrage en une commande (Windows)
REM   start.bat
cd /d "%~dp0"

if not exist venv (
  echo Creation de l'environnement Python...
  python -m venv venv
)

call venv\Scripts\activate

echo Installation des dependances...
pip install -q -r requirements.txt

echo Lancement d'AI OS...
python run.py
