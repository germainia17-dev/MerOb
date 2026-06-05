<div align="center">

# Obsidian Chat Memory

**Turn your ChatGPT, Claude & Gemini conversations into a self-organizing Obsidian knowledge graph — automatically, locally, for free.**

[Install](#install) · [How it works](#how-it-works) · [Why](#why-this-exists) · [Roadmap](#roadmap)

<!-- Record a 20s GIF and drop it at docs/demo.gif — see docs/RECORD_DEMO.md -->
![demo](docs/demo.gif)

</div>

---

Your best thinking happens inside AI chats — and then dies in a history you'll never reopen.
**Obsidian Chat Memory** captures the insights from your conversations and files them into your
own Obsidian vault as individual, linked notes. Over time, a knowledge graph grows itself.

- 🧠 **Works across ChatGPT, Claude and Gemini** — one brain for all three, captured from the web UI.
- 📂 **Lands in *your* Obsidian vault** — plain Markdown notes you own forever. Not a SaaS silo.
- 🔒 **100% local, $0 / month** — embeddings run on your machine. The only network call is one
  Gemini request per extraction.
- 🕸️ **Builds a graph, not a list** — one note per memory, auto-linked to its neighbors, grouped
  into categories the tool discovers on its own as your vault grows.
- ↩️ **Remembers you back** — as you type in any chat, relevant memories surface and can be
  injected into your prompt in one click.

> **Why not just use ChatGPT's built-in memory?** Because it's siloed (Claude can't see it),
> it's not in *your* files, and you can't grep it, link it, or keep it for 10 years. This is
> *your* memory, in *your* vault.

> ⭐ **If this idea resonates, star the repo** — it's the single best way to help other
> people stop losing their best AI conversations.

## Install

Full step-by-step guide in **[INSTALL.md](INSTALL.md)**. The short version:

```bash
git clone https://github.com/<you>/obsidian-chat-memory
cd obsidian-chat-memory

# macOS / Linux
./start.sh
# Windows
start.bat
```

On first run it auto-detects your Obsidian vault, asks for a free
[Gemini API key](https://aistudio.google.com/apikey), and starts the local server.
Then load the `chrome_extension/` folder in `chrome://extensions` (Developer mode →
*Load unpacked*) and open ChatGPT, Claude or Gemini.

**Requirements:** Python 3.10+, Obsidian, a Chromium browser.

## How it works

```
   Chat (ChatGPT / Claude / Gemini)
            │  click "Extract"
            ▼
   Gemini extracts the worth-keeping memories      ← 1 API call
            │
            ▼
   Local pipeline (0 API, runs on your machine)
     • dedupe / update against existing notes
     • file each memory into its category (tagged during extraction;
       local embeddings as fallback)
     • write one Markdown note per memory + wikilinks
     • group related memories, discover new categories
            ▼
   Your Obsidian vault  →  Memories/  +  Categories/
```

Everything after the extraction step runs locally with
[`fastembed`](https://github.com/qdrant/fastembed) (ONNX, ~50 MB — no PyTorch) and
cosine similarity. Beyond that single extraction call, no data leaves your machine —
storage, search, dedup and graph-building all happen locally.

### Reinjection

A floating panel on ChatGPT / Claude / Gemini searches your memories as you type and lets you
inject the relevant ones into your prompt — so the assistant starts the conversation already
knowing you.

## Why this exists

The "AI memory" space is crowded, but almost everything is either a **cloud SaaS** that owns your
data, or a **coding-agent** memory tool. This is different on purpose:

|                         | Native chat memory | Cloud memory SaaS | **Obsidian Chat Memory** |
| ----------------------- | :----------------: | :---------------: | :----------------------: |
| Works across ChatGPT + Claude + Gemini | ❌ | ⚠️ | ✅ |
| Your data in plain Markdown you own     | ❌ | ❌ | ✅ |
| Fully local / free                      | ❌ | ❌ | ✅ |
| Becomes an explorable knowledge graph   | ❌ | ⚠️ | ✅ |

## Roadmap

- [x] One note per memory + wikilinks (organic graph)
- [x] Local dedupe / update / classification (0 API)
- [x] Hybrid auto-discovery of new categories
- [x] One-command, cross-platform install
- [ ] Smarter category naming (occasional LLM pass)
- [ ] Native Obsidian plugin (drop the browser-extension + server setup)
- [ ] Conflict detection (memories that contradict older ones)

## Support

If this tool saves you from re-explaining yourself to every AI, **a ⭐ helps other people
find it** — it's the simplest way to support the project. Found a bug or have an idea?
[Open an issue](../../issues) — feedback shapes the roadmap.

## License

MIT — see [LICENSE](LICENSE).
