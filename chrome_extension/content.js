// ======================
// Obsidian Chat Memory — content script
// Fonctionne sur ChatGPT, Claude, Gemini
// Appelle le serveur local FastAPI (localhost:8000)
// ======================

const API = "http://localhost:8000";
let panel, searchTimeout;

// ======================
// DÉTECTION DU SITE
// ======================

function getSite() {
  const h = location.hostname;
  if (h.includes("chatgpt.com") || h.includes("openai.com")) return "chatgpt";
  if (h.includes("claude.ai"))   return "claude";
  if (h.includes("gemini"))      return "gemini";
  return null;
}

// Sélecteurs de la zone de saisie selon le site
function getInputSelector() {
  const site = getSite();
  if (site === "chatgpt") return "#prompt-textarea";
  if (site === "claude")  return 'div[contenteditable="true"]';
  if (site === "gemini")  return 'rich-textarea div[contenteditable="true"]';
  return null;
}

// ======================
// PANNEAU FLOTTANT
// ======================

function createPanel() {
  const el = document.createElement("div");
  el.id = "aios-panel";
  el.innerHTML = `
    <div id="aios-header">
      <span>🧠 Obsidian Chat Memory</span>
      <div id="aios-controls">
        <button id="aios-extract-btn" title="Extraire les mémoires de cette conversation">⬆ Extraire</button>
        <button id="aios-toggle" title="Réduire">−</button>
      </div>
    </div>
    <div id="aios-body">
      <input id="aios-search" placeholder="Rechercher une mémoire…" autocomplete="off"/>
      <div id="aios-results">
        <p class="aios-hint">Les mémoires pertinentes apparaîtront ici.</p>
      </div>
      <div id="aios-inject-bar">
        <button id="aios-inject-btn" style="display:none">⬇ Injecter dans le prompt</button>
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
      background: #1e1e2e;
      color: #cdd6f4;
      border-radius: 12px;
      font-family: sans-serif;
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
      background: #313244;
      border-radius: 12px 12px 0 0;
      font-weight: bold;
      cursor: move;
    }
    #aios-controls { display: flex; gap: 6px; }
    #aios-controls button {
      background: #45475a;
      color: #cdd6f4;
      border: none;
      border-radius: 6px;
      padding: 3px 8px;
      cursor: pointer;
      font-size: 12px;
    }
    #aios-controls button:hover { background: #585b70; }
    #aios-body { padding: 10px; display: flex; flex-direction: column; gap: 8px; overflow: hidden; }
    #aios-search {
      width: 100%;
      box-sizing: border-box;
      padding: 7px 10px;
      border-radius: 8px;
      border: 1px solid #45475a;
      background: #313244;
      color: #cdd6f4;
      font-size: 13px;
      outline: none;
    }
    #aios-results {
      overflow-y: auto;
      max-height: 260px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .aios-hint { color: #6c7086; font-size: 12px; margin: 0; }
    .aios-card {
      background: #313244;
      border-radius: 8px;
      padding: 8px 10px;
      border-left: 3px solid #89b4fa;
      cursor: pointer;
      transition: background 0.15s;
    }
    .aios-card:hover { background: #45475a; }
    .aios-card .aios-source {
      font-size: 10px;
      color: #6c7086;
      margin-bottom: 3px;
    }
    .aios-card.selected { border-left-color: #a6e3a1; }
    #aios-inject-btn {
      width: 100%;
      padding: 7px;
      background: #89b4fa;
      color: #1e1e2e;
      border: none;
      border-radius: 8px;
      font-weight: bold;
      cursor: pointer;
      font-size: 13px;
    }
    #aios-inject-btn:hover { background: #b4befe; }
    #aios-panel.minimized #aios-body { display: none; }
    #aios-panel.minimized { max-height: 44px; }
  `;

  document.head.appendChild(style);
  document.body.appendChild(el);

  return el;
}

// ======================
// RECHERCHE
// ======================

async function search(query) {
  const res = document.getElementById("aios-results");
  res.innerHTML = '<p class="aios-hint">Recherche…</p>';

  try {
    const r = await fetch(`${API}/memories/search?q=${encodeURIComponent(query)}&n=5`);
    const data = await r.json();

    if (!data.results || data.results.length === 0) {
      res.innerHTML = '<p class="aios-hint">Aucune mémoire trouvée.</p>';
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
    res.innerHTML = '<p class="aios-hint">⚠ Serveur local inaccessible.<br>Lance : uvicorn server:app --port 8000</p>';
  }
}

// ======================
// INJECTION DANS LE PROMPT
// ======================

function injectIntoPrompt() {
  const selected = [...document.querySelectorAll(".aios-card.selected")];
  const cards    = selected.length > 0 ? selected : [...document.querySelectorAll(".aios-card")];

  if (cards.length === 0) return;

  const memories = cards.map(c => "- " + c.dataset.content).join("\n");
  const context  = `[Mémoires personnelles]\n${memories}\n\n`;

  const selector = getInputSelector();
  if (!selector) return;

  const input = document.querySelector(selector);
  if (!input) return;

  // ChatGPT utilise un textarea, Claude/Gemini un div contenteditable
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
// EXTRACTION EN FIN DE CONVERSATION
// ======================

async function extractConversation() {
  // Récupère le texte visible de la page comme proxy de la conversation
  const msgs = [...document.querySelectorAll(
    '[data-message-author-role], .human-turn, .model-turn, ' +
    '.human, .assistant, [class*="message"]'
  )].map(el => el.innerText).filter(Boolean).join("\n\n");

  if (!msgs.trim()) {
    alert("Aucun contenu de conversation trouvé sur la page.");
    return;
  }

  const btn = document.getElementById("aios-extract-btn");
  btn.textContent = "⏳ Envoi…";
  btn.disabled = true;

  try {
    const r = await fetch(`${API}/extract`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation: msgs })
    });
    const data = await r.json();
    alert("✅ " + (data.message || "Mémoires extraites."));
  } catch (e) {
    alert("⚠ Serveur local inaccessible.\nLance : uvicorn server:app --port 8000");
  } finally {
    btn.textContent = "⬆ Extraire";
    btn.disabled = false;
  }
}

// ======================
// DRAG (déplacer le panneau)
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

  // Minimiser/maximiser
  document.getElementById("aios-toggle").addEventListener("click", () => {
    panel.classList.toggle("minimized");
    document.getElementById("aios-toggle").textContent =
      panel.classList.contains("minimized") ? "+" : "−";
  });

  // Recherche manuelle
  document.getElementById("aios-search").addEventListener("input", e => {
    clearTimeout(searchTimeout);
    const q = e.target.value.trim();
    if (q.length < 2) return;
    searchTimeout = setTimeout(() => search(q), 400);
  });

  // Recherche auto sur la frappe dans l'input principal
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

  // Injecter
  document.getElementById("aios-inject-btn").addEventListener("click", injectIntoPrompt);

  // Extraire
  document.getElementById("aios-extract-btn").addEventListener("click", extractConversation);
}

// Attend que la page soit prête (les SPA chargent en retard)
if (document.readyState === "complete") {
  init();
} else {
  window.addEventListener("load", init);
}
