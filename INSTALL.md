# Installation

From zero to working in ~5 minutes.

## Requirements

- **Python 3.10+** ([download](https://www.python.org/downloads/))
- **Obsidian** with at least one vault open
- A **Chrome / Edge / Brave** browser
- A **Gemini API key** (free: https://aistudio.google.com/apikey)

## 1. Start the server

```bash
git clone https://github.com/<you>/obsidian-chat-memory
cd obsidian-chat-memory

# macOS / Linux
./start.sh

# Windows
start.bat
```

On first launch, the script:
1. creates the Python environment and installs the dependencies,
2. **auto-detects your Obsidian vault** (or asks you for the path),
3. asks for your **Gemini key** (stored in `.env`),
4. starts the server on http://localhost:8000.

Leave this window open. Check that it's running:
👉 http://localhost:8000/health should return `{"status":"ok", ...}`.

> No `start.sh`? Manual equivalent:
> ```bash
> python3 -m venv venv && source venv/bin/activate
> pip install --upgrade pip && pip install -r requirements.txt
> python run.py
> ```

## 2. Install the browser extension

1. Open `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select the `chrome_extension/` folder
5. Open ChatGPT, Claude or Gemini → the MerOb panel appears bottom-right

## 3. Use it

- **Capture**: at the end of a conversation, click **⬆ Extract**. The memories
  are filed automatically into your Obsidian vault (`Memories/` + `Categories/`).
- **Reinject**: type your message — relevant memories surface in the panel.
  Click **⬇ Inject into prompt** to paste them into your prompt.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Python 3.10+ required` | Install a recent version of Python |
| Panel says "Server unreachable" | The server isn't running → re-run `./start.sh` |
| "Gemini API key missing" | Run `python config.py` or edit `.env` |
| Wrong vault detected | Edit `config.json` (`"vault"` key) with the correct path |
| No memories found | Check `http://localhost:8000/health` → `vault` field |
