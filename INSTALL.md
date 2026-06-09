# Installation Guide — MerOb

Complete step-by-step instructions for setting up MerOb. Takes ~5 minutes.

---

## 📋 Prerequisites

Before you start, make sure you have:

| Requirement | Link | Notes |
|---|---|---|
| **Python 3.10+** | [Download](https://www.python.org/downloads/) | Check with `python3 --version` |
| **Obsidian** | [Download](https://obsidian.md/) | Create or open a vault first |
| **Chrome / Edge / Brave** | Built-in | Firefox support coming soon |
| **Gemini API Key** | [Get Free](https://aistudio.google.com/apikey) | Free tier includes generous limits |

Verify Python is installed:
```bash
python3 --version  # Should be 3.10 or higher
```

---

## ⚙️ Step 1: Clone & Start the Server

```bash
# Clone the repo
git clone https://github.com/germainia17-dev/MerOb.git
cd MerOb

# macOS / Linux
./start.sh

# Windows
start.bat
```

**On first run**, the script will:
1. ✅ Create a Python virtual environment
2. ✅ Install dependencies
3. ❓ Ask for your **Obsidian vault path** (or auto-detect it)
4. ❓ Ask for your **Gemini API key** (saves to `.env`)
5. ✅ Start the server on `http://localhost:8000`

**Keep this terminal window open** — it's your server.

### Manual Setup (if `start.sh` doesn't work)

```bash
python3 -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate           # Windows

pip install --upgrade pip
pip install -r requirements.txt

python run.py
```

**Verify it's running:**
```bash
curl http://localhost:8000/health
# Should return: {"status":"ok", "vault":"..."}
```

---

## 🧩 Step 2: Install the Chrome Extension

1. **Open Chrome** and go to `chrome://extensions`
2. **Enable Developer Mode** (toggle in top-right corner)
3. **Click "Load unpacked"**
4. **Select the `chrome_extension/` folder** from your cloned repo
5. **You should see the MerOb icon** in your toolbar

The extension is now installed and ready to use.

---

## 🚀 Step 3: Use MerOb

### Extracting Memories

1. **Open ChatGPT, Claude, or Gemini** in your browser
2. **Have a conversation** with the AI
3. **Click the MerOb icon** in your toolbar → the panel opens bottom-right
4. **Click "Extract"** to save key insights
5. **Check Obsidian** → new notes appear in `Memories/` and `Categories/`

### Injecting Memories

1. **Start typing a new prompt** in any chat
2. **Relevant memories appear** in the MerOb panel automatically
3. **Click "Inject"** to paste them into your prompt
4. The AI now knows your past context!

---

## 🔧 Configuration

### Change Your Vault

Edit `config.json` in the project root:

```json
{
  "vault": "/path/to/your/obsidian/vault",
  "categories_folder": "Categories",
  "memories_folder": "Memories"
}
```

### Update Your Gemini Key

```bash
# Edit the .env file
nano .env

# Or run:
python config.py
```

---

## 🐛 Troubleshooting

### "Python 3.10+ required"
```bash
# Upgrade Python
python3 --version  # Check current version
# Download 3.10+ from python.org
```

### "Server unreachable" in the panel
```bash
# Make sure the server is running
curl http://localhost:8000/health

# If not, restart it:
./start.sh  # macOS/Linux
start.bat   # Windows
```

### "Gemini API key missing"
```bash
# Edit the .env file
nano .env
# Add: GEMINI_API_KEY=your_key_here

# Or run the config wizard:
python config.py
```

### Wrong Obsidian vault detected
```bash
# Edit config.json and set the correct path
nano config.json

# Example:
# "vault": "/Users/username/Documents/MyVault"
```

### "No memories found"
1. Check that the vault path is correct: `http://localhost:8000/health`
2. Make sure you have write permissions to the vault folder
3. Try extracting from a new conversation

### Extension icon not showing
1. Refresh `chrome://extensions`
2. Make sure you selected the correct `chrome_extension/` folder
3. Restart Chrome

---

## 📤 Updating MerOb

To get the latest version:

```bash
git pull origin main
pip install -r requirements.txt
./start.sh  # Restart the server
```

---

## ❌ Uninstall

1. **Remove the extension:** Go to `chrome://extensions` → click "Remove"
2. **Delete the folder:** `rm -rf merob` (or delete via Finder/Explorer)
3. **Your Obsidian vault remains untouched** — all your memories are safe

---

## 🆘 Still Stuck?

- 📖 Check the [README](README.md)
- 🐛 [Report a bug](../../issues)
- 💬 [Start a discussion](../../discussions)
- 📧 Email: germain.ia17@gmail.com

---

**You're all set!** Happy memory-making. 🧠✨
