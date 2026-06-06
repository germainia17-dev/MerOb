// ======================
// MerOb (Memory · Obsidian) — content script
// Works on ChatGPT, Claude, Gemini
// Calls the local FastAPI server (localhost:8000)
// ======================

const API = "http://localhost:8000";
let panel, searchTimeout;

// ======================
// SITE DETECTION
// ======================

function getSite() {
  const h = location.hostname;
  if (h.includes("chatgpt.com") || h.includes("openai.com")) return "chatgpt";
  if (h.includes("claude.ai"))   return "claude";
  if (h.includes("gemini"))      return "gemini";
  return null;
}

// Input-area selectors per site
function getInputSelector() {
  const site = getSite();
  if (site === "chatgpt") return "#prompt-textarea";
  if (site === "claude")  return 'div[contenteditable="true"]';
  if (site === "gemini")  return 'rich-textarea div[contenteditable="true"]';
  return null;
}

// ======================
// FLOATING PANEL
// ======================

function createPanel() {
  const el = document.createElement("div");
  el.id = "aios-panel";
  el.innerHTML = `
    <div id="aios-header">
      <span class="aios-brand">
        <svg width="18" height="18" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
          <circle cx="60" cy="60" r="10.5" fill="#7c6fff"/>
          <circle cx="27" cy="36" r="6" fill="#7c6fff" opacity="0.7"/>
          <circle cx="93" cy="36" r="6" fill="#7c6fff" opacity="0.7"/>
          <circle cx="27" cy="84" r="6" fill="#7c6fff" opacity="0.5"/>
          <circle cx="93" cy="84" r="6" fill="#7c6fff" opacity="0.5"/>
          <line x1="60" y1="60" x2="27" y2="36" stroke="#7c6fff" stroke-width="1.5" opacity="0.55"/>
          <line x1="60" y1="60" x2="93" y2="36" stroke="#7c6fff" stroke-width="1.5" opacity="0.55"/>
          <line x1="60" y1="60" x2="27" y2="84" stroke="#7c6fff" stroke-width="1.5" opacity="0.4"/>
          <line x1="60" y1="60" x2="93" y2="84" stroke="#7c6fff" stroke-width="1.5" opacity="0.4"/>
        </svg>
        MerOb
      </span>
      <div id="aios-controls">
        <button id="aios-extract-btn" title="Extract memories from this conversation">⬆ Extract</button>
        <button id="aios-toggle" title="Minimize">−</button>
        <button id="aios-close" title="Close">×</button>
      </div>
    </div>
    <div id="aios-body">
      <input id="aios-search" placeholder="Search memories…" autocomplete="off"/>
      <div id="aios-results">
        <p class="aios-hint">Relevant memories will appear here.</p>
      </div>
      <div id="aios-inject-bar">
        <button id="aios-inject-btn" style="display:none">⬇ Inject into prompt</button>
      </div>
    </div>
  `;

  const style = document.createElement("style");
  style.textContent = `
    #aios-panel {
      position: fixed;
      bottom: 80px;
      right: 20px;
      width: 320px;
      max-height: 420px;
      background: #0f0f17;
      color: #f5f4f0;
      border: 1px solid #20202e;
      border-radius: 12px;
      font-family: 'Syne', 'Segoe UI', sans-serif;
      font-size: 13px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.5);
      z-index: 99999;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    #aios-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 14px;
      background: #1a1a26;
      border-radius: 12px 12px 0 0;
      font-weight: 800;
      letter-spacing: -0.3px;
      cursor: move;
    }
    .aios-brand { display: flex; align-items: center; gap: 7px; }
    .aios-brand svg { flex: none; }
    #aios-controls { display: flex; gap: 6px; }
    #aios-controls button {
      background: #26263a;
      color: #f5f4f0;
      border: none;
      border-radius: 6px;
      padding: 3px 8px;
      cursor: pointer;
      font-size: 12px;
    }
    #aios-controls button:hover { background: #353550; }
    #aios-body { padding: 10px; display: flex; flex-direction: column; gap: 8px; overflow: hidden; }
    #aios-search {
      width: 100%;
      box-sizing: border-box;
      padding: 7px 10px;
      border-radius: 8px;
      border: 1px solid #2a2a3a;
      background: #1a1a26;
      color: #f5f4f0;
      font-size: 13px;
      outline: none;
    }
    #aios-search:focus { border-color: #7c6fff; }
    #aios-results {
      overflow-y: auto;
      max-height: 260px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .aios-hint { color: #6b6880; font-size: 12px; margin: 0; }
    .aios-card {
      background: #1a1a26;
      border-radius: 8px;
      padding: 8px 10px;
      border-left: 3px solid #7c6fff;
      cursor: pointer;
      transition: background 0.15s;
    }
    .aios-card:hover { background: #26263a; }
    .aios-card .aios-source {
      font-size: 10px;
      color: #6b6880;
      margin-bottom: 3px;
    }
    .aios-card.selected { border-left-color: #b8b0ff; background: #26263a; }
    #aios-inject-btn {
      width: 100%;
      padding: 7px;
      background: #7c6fff;
      color: #0f0f17;
      border: none;
      border-radius: 8px;
      font-weight: bold;
      cursor: pointer;
      font-size: 13px;
    }
    #aios-inject-btn:hover { background: #b8b0ff; }
    #aios-panel.minimized #aios-body { display: none; }
    #aios-panel.minimized { max-height: 44px; }
    #aios-close:hover { background: #ff8fa3 !important; color: #0f0f17; }
    #aios-launcher {
      position: fixed;
      bottom: 20px;
      right: 20px;
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: #1a1a26;
      border: 1px solid #20202e;
      display: none;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 4px 16px rgba(0,0,0,0.5);
      z-index: 99999;
      user-select: none;
    }
    #aios-launcher:hover { background: #26263a; }
  `;

  document.head.appendChild(style);
  document.body.appendChild(el);

  // Floating launcher to reopen the panel after it has been closed
  const launcher = document.createElement("div");
  launcher.id = "aios-launcher";
  launcher.title = "Open MerOb";
  launcher.innerHTML = `
    <svg width="26" height="26" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
      <circle cx="60" cy="60" r="10.5" fill="#7c6fff"/>
      <circle cx="27" cy="36" r="6" fill="#7c6fff" opacity="0.7"/>
      <circle cx="93" cy="36" r="6" fill="#7c6fff" opacity="0.7"/>
      <circle cx="27" cy="84" r="6" fill="#7c6fff" opacity="0.5"/>
      <circle cx="93" cy="84" r="6" fill="#7c6fff" opacity="0.5"/>
      <line x1="60" y1="60" x2="27" y2="36" stroke="#7c6fff" stroke-width="1.5" opacity="0.55"/>
      <line x1="60" y1="60" x2="93" y2="36" stroke="#7c6fff" stroke-width="1.5" opacity="0.55"/>
      <line x1="60" y1="60" x2="27" y2="84" stroke="#7c6fff" stroke-width="1.5" opacity="0.4"/>
      <line x1="60" y1="60" x2="93" y2="84" stroke="#7c6fff" stroke-width="1.5" opacity="0.4"/>
    </svg>
  `;
  document.body.appendChild(launcher);

  return el;
}

// ======================
// SEARCH
// ======================

async function search(query) {
  const res = document.getElementById("aios-results");
  res.innerHTML = '<p class="aios-hint">Searching…</p>';

  try {
    const r = await fetch(`${API}/memories/search?q=${encodeURIComponent(query)}&n=5`);
    const data = await r.json();

    if (!data.results || data.results.length === 0) {
      res.innerHTML = '<p class="aios-hint">No memories found.</p>';
      document.getElementById("aios-inject-btn").style.display = "none";
      return;
    }

    res.innerHTML = "";
    data.results.forEach(item => {
      const card = document.createElement("div");
      card.className = "aios-card";
      card.dataset.content = item.content;
      card.innerHTML = `
        <div class="aios-source">${item.file || item.source} ${item.score ? "· " + item.score : ""}</div>
        <div>${item.content}</div>
      `;
      card.addEventListener("click", () => card.classList.toggle("selected"));
      res.appendChild(card);
    });

    document.getElementById("aios-inject-btn").style.display = "block";

  } catch (e) {
    res.innerHTML = '<p class="aios-hint">⚠ Local server unreachable.<br>Run: python run.py</p>';
  }
}

// ======================
// INJECT INTO PROMPT
// ======================

function injectIntoPrompt() {
  const selected = [...document.querySelectorAll(".aios-card.selected")];
  const cards    = selected.length > 0 ? selected : [...document.querySelectorAll(".aios-card")];

  if (cards.length === 0) return;

  const memories = cards.map(c => "- " + c.dataset.content).join("\n");
  const context  = `[Personal memories]\n${memories}\n\n`;

  const selector = getInputSelector();
  if (!selector) return;

  const input = document.querySelector(selector);
  if (!input) return;

  // ChatGPT uses a textarea, Claude/Gemini a contenteditable div
  if (input.tagName === "TEXTAREA") {
    const pos = input.selectionStart || 0;
    input.value = context + input.value.slice(pos);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  } else {
    input.focus();
    document.execCommand("insertText", false, context);
  }
}

// ======================
// EXTRACT AT END OF CONVERSATION
// ======================

async function extractConversation() {
  // Grab the page's visible text as a proxy for the conversation
  const msgs = [...document.querySelectorAll(
    '[data-message-author-role], .human-turn, .model-turn, ' +
    '.human, .assistant, [class*="message"]'
  )].map(el => el.innerText).filter(Boolean).join("\n\n");

  if (!msgs.trim()) {
    alert("No conversation content found on this page.");
    return;
  }

  const btn = document.getElementById("aios-extract-btn");
  btn.textContent = "⏳ Sending…";
  btn.disabled = true;

  try {
    const r = await fetch(`${API}/extract`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation: msgs })
    });
    const data = await r.json();
    alert("✅ " + (data.message || "Memories extracted."));
  } catch (e) {
    alert("⚠ Local server unreachable.\nRun: python run.py");
  } finally {
    btn.textContent = "⬆ Extract";
    btn.disabled = false;
  }
}

// ======================
// DRAG (move the panel)
// ======================

function makeDraggable(panel) {
  const header = document.getElementById("aios-header");
  let dragging = false, ox = 0, oy = 0;

  header.addEventListener("mousedown", e => {
    dragging = true;
    ox = e.clientX - panel.getBoundingClientRect().left;
    oy = e.clientY - panel.getBoundingClientRect().top;
  });
  document.addEventListener("mousemove", e => {
    if (!dragging) return;
    panel.style.left   = (e.clientX - ox) + "px";
    panel.style.top    = (e.clientY - oy) + "px";
    panel.style.right  = "auto";
    panel.style.bottom = "auto";
  });
  document.addEventListener("mouseup", () => dragging = false);
}

// ======================
// INIT
// ======================

function init() {
  if (!getSite()) return;
  if (document.getElementById("aios-panel")) return;

  panel = createPanel();
  makeDraggable(panel);

  // Minimize / maximize
  document.getElementById("aios-toggle").addEventListener("click", () => {
    panel.classList.toggle("minimized");
    document.getElementById("aios-toggle").textContent =
      panel.classList.contains("minimized") ? "+" : "−";
  });

  // Close → hide the panel and show the floating launcher to reopen it
  const launcher = document.getElementById("aios-launcher");
  document.getElementById("aios-close").addEventListener("click", () => {
    panel.style.display = "none";
    launcher.style.display = "flex";
  });
  launcher.addEventListener("click", () => {
    panel.classList.remove("minimized");
    document.getElementById("aios-toggle").textContent = "−";
    panel.style.display = "flex";
    launcher.style.display = "none";
  });

  // Manual search
  document.getElementById("aios-search").addEventListener("input", e => {
    clearTimeout(searchTimeout);
    const q = e.target.value.trim();
    if (q.length < 2) return;
    searchTimeout = setTimeout(() => search(q), 400);
  });

  // Auto-search as the user types in the main input
  const selector = getInputSelector();
  if (selector) {
    const observer = new MutationObserver(() => {
      const input = document.querySelector(selector);
      if (input && !input.dataset.aiosListening) {
        input.dataset.aiosListening = "1";
        input.addEventListener("input", e => {
          clearTimeout(searchTimeout);
          const text = (e.target.value || e.target.innerText || "").slice(-120).trim();
          if (text.length < 3) return;
          searchTimeout = setTimeout(() => search(text), 600);
        });
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  // Inject
  document.getElementById("aios-inject-btn").addEventListener("click", injectIntoPrompt);

  // Extract
  document.getElementById("aios-extract-btn").addEventListener("click", extractConversation);
}

// Wait for the page to be ready (SPAs load late)
if (document.readyState === "complete") {
  init();
} else {
  window.addEventListener("load", init);
}
