@echo off
REM Obsidian Chat Memory - one-command start (Windows)
REM   start.bat
cd /d "%~dp0"

REM Guard: Python 3.10+ required
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>nul
if errorlevel 1 (
  echo Obsidian Chat Memory requires Python 3.10+.
  echo Download a recent version from https://www.python.org/downloads/
  exit /b 1
)

if not exist venv (
  echo Creating Python environment...
  python -m venv venv
)

call venv\Scripts\activate

echo Updating pip...
pip install -q --upgrade pip

echo Installing dependencies...
pip install -q -r requirements.txt

echo Starting Obsidian Chat Memory...
python run.py
