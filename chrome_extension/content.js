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
  el.id = "merob-panel";
  el.innerHTML = `
    <div id="merob-header">
      <div class="merob-brand">
        <svg width="20" height="20" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
          <circle cx="60" cy="60" r="10.5" fill="#5E6AD2"/>
          <circle cx="27" cy="36" r="6" fill="#5E6AD2" opacity="0.7"/>
          <circle cx="93" cy="36" r="6" fill="#5E6AD2" opacity="0.7"/>
          <circle cx="27" cy="84" r="6" fill="#5E6AD2" opacity="0.5"/>
          <circle cx="93" cy="84" r="6" fill="#5E6AD2" opacity="0.5"/>
          <line x1="60" y1="60" x2="27" y2="36" stroke="#8A8F98" stroke-width="1.5" opacity="0.55"/>
          <line x1="60" y1="60" x2="93" y2="36" stroke="#8A8F98" stroke-width="1.5" opacity="0.55"/>
          <line x1="60" y1="60" x2="27" y2="84" stroke="#8A8F98" stroke-width="1.5" opacity="0.4"/>
          <line x1="60" y1="60" x2="93" y2="84" stroke="#8A8F98" stroke-width="1.5" opacity="0.4"/>
        </svg>
        <span class="merob-title">MerOb</span>
      </div>
      <div id="merob-controls">
        <button id="merob-extract-btn" class="merob-btn merob-btn-primary" title="Extract memories from this conversation">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
            <path d="M8 2v8m0-8L4.5 5.5M8 2l3.5 3.5M2 13h12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Extract
        </button>
        <button id="merob-toggle" class="merob-ctrl-btn" title="Minimize">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M4 8h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
        </button>
        <button id="merob-close" class="merob-ctrl-btn" title="Close">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
        </button>
      </div>
    </div>
    <div id="merob-body">
      <div class="merob-search-wrap">
        <svg class="merob-search-icon" width="14" height="14" viewBox="0 0 16 16" fill="none">
          <circle cx="7" cy="7" r="5" stroke="currentColor" stroke-width="1.5"/>
          <path d="M11 11l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <input id="merob-search" placeholder="Search your memories…" autocomplete="off" spellcheck="false"/>
      </div>
      <div id="merob-results">
        <div class="merob-empty-hint">
          <svg width="24" height="24" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" opacity="0.3">
            <circle cx="60" cy="60" r="10.5" fill="#5E6AD2"/>
            <circle cx="27" cy="36" r="6" fill="#5E6AD2" opacity="0.7"/>
            <circle cx="93" cy="36" r="6" fill="#5E6AD2" opacity="0.7"/>
            <circle cx="27" cy="84" r="6" fill="#5E6AD2" opacity="0.5"/>
            <circle cx="93" cy="84" r="6" fill="#5E6AD2" opacity="0.5"/>
            <line x1="60" y1="60" x2="27" y2="36" stroke="#8A8F98" stroke-width="1.5" opacity="0.55"/>
            <line x1="60" y1="60" x2="93" y2="36" stroke="#8A8F98" stroke-width="1.5" opacity="0.55"/>
            <line x1="60" y1="60" x2="27" y2="84" stroke="#8A8F98" stroke-width="1.5" opacity="0.4"/>
            <line x1="60" y1="60" x2="93" y2="84" stroke="#8A8F98" stroke-width="1.5" opacity="0.4"/>
          </svg>
          <span>Relevant memories will surface as you type</span>
        </div>
      </div>
      <div id="merob-inject-bar">
        <button id="merob-inject-btn" class="merob-btn merob-btn-accent" style="display:none">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
            <path d="M8 14V6m0 8L4.5 10.5M8 14l3.5-3.5M2 3h12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Inject selected into prompt
        </button>
      </div>
    </div>
  `;

  const style = document.createElement("style");
  style.textContent = `
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Syne:wght@600;700&display=swap');

    #merob-panel {
      position: fixed;
      bottom: 80px;
      right: 20px;
      width: 360px;
      max-height: 480px;
      background: rgba(17, 19, 20, 0.85);
      color: #F2F2F2;
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 12px;
      font-family: 'Inter', -apple-system, sans-serif;
      font-size: 13px;
      box-shadow:
        0 24px 48px rgba(0, 0, 0, 0.4),
        0 8px 16px rgba(0, 0, 0, 0.4),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
      z-index: 99999;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      animation: merob-slide-up 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      backdrop-filter: blur(20px);
      -webkit-font-smoothing: antialiased;
    }

    @keyframes merob-slide-up {
      from { opacity: 0; transform: translateY(12px) scale(0.98); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    #merob-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      cursor: move;
      user-select: none;
    }

    .merob-brand {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .merob-brand svg { flex-shrink: 0; filter: drop-shadow(0 2px 4px rgba(94,106,210,0.3)); }

    .merob-title {
      font-family: 'Syne', sans-serif;
      font-size: 15px;
      font-weight: 700;
      letter-spacing: -0.2px;
      background: linear-gradient(180deg, #fff, #a1a1aa);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    #merob-controls {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .merob-ctrl-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 26px;
      height: 26px;
      background: transparent;
      color: #8A8F98;
      border: 1px solid transparent;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .merob-ctrl-btn:hover {
      background: rgba(255, 255, 255, 0.06);
      color: #F2F2F2;
      border-color: rgba(255, 255, 255, 0.08);
    }

    #merob-close:hover {
      background: rgba(248, 81, 73, 0.1) !important;
      color: #F85149 !important;
    }

    .merob-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 6px;
      font-family: 'Inter', sans-serif;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s ease;
      white-space: nowrap;
      box-shadow: 0 1px 2px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.02);
    }

    .merob-btn-primary {
      background: #F2F2F2;
      color: #111314;
      border: none;
    }

    .merob-btn-primary:hover {
      background: #ffffff;
      box-shadow: 0 2px 8px rgba(255,255,255,0.15);
      transform: translateY(-1px);
    }

    .merob-btn-primary:active {
      transform: translateY(0);
    }

    .merob-btn-primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none;
    }

    .merob-btn-accent {
      width: 100%;
      padding: 8px;
      justify-content: center;
      background: rgba(94, 106, 210, 0.1);
      color: #5E6AD2;
      border: 1px solid rgba(94, 106, 210, 0.2);
    }

    .merob-btn-accent:hover {
      background: rgba(94, 106, 210, 0.2);
      color: #fff;
    }

    #merob-body {
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      overflow: hidden;
    }

    .merob-search-wrap {
      position: relative;
    }

    .merob-search-icon {
      position: absolute;
      left: 10px;
      top: 50%;
      transform: translateY(-50%);
      color: #8A8F98;
      pointer-events: none;
      transition: color 0.15s;
    }

    #merob-search {
      width: 100%;
      box-sizing: border-box;
      padding: 8px 12px 8px 30px;
      border-radius: 6px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      background: rgba(0, 0, 0, 0.2);
      color: #F2F2F2;
      font-family: 'Inter', sans-serif;
      font-size: 13px;
      outline: none;
      transition: all 0.2s ease;
      box-shadow: inset 0 1px 2px rgba(0,0,0,0.3);
    }

    #merob-search::placeholder {
      color: #8A8F98;
    }

    #merob-search:focus {
      border-color: rgba(94, 106, 210, 0.5);
      background: rgba(0, 0, 0, 0.3);
      box-shadow: 0 0 0 2px rgba(94, 106, 210, 0.2), inset 0 1px 2px rgba(0,0,0,0.3);
    }

    #merob-search:focus ~ .merob-search-icon,
    .merob-search-wrap:focus-within .merob-search-icon {
      color: #5E6AD2;
    }

    #merob-results {
      overflow-y: auto;
      max-height: 280px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      scrollbar-width: thin;
      scrollbar-color: rgba(255, 255, 255, 0.1) transparent;
    }

    #merob-results::-webkit-scrollbar {
      width: 4px;
    }

    #merob-results::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 4px;
    }

    .merob-empty-hint {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      padding: 32px 10px;
      color: #8A8F98;
      font-size: 12px;
      text-align: center;
    }

    .merob-card {
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 8px;
      padding: 12px;
      cursor: pointer;
      transition: all 0.2s ease;
      position: relative;
      animation: merob-card-in 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      opacity: 0;
    }

    @keyframes merob-card-in {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .merob-card:hover {
      background: rgba(255, 255, 255, 0.04);
      border-color: rgba(255, 255, 255, 0.12);
    }

    .merob-card.selected {
      background: rgba(94, 106, 210, 0.1);
      border-color: rgba(94, 106, 210, 0.3);
    }

    .merob-card.selected::before {
      content: '';
      position: absolute;
      left: 0;
      top: 10px;
      bottom: 10px;
      width: 2px;
      background: #5E6AD2;
      border-radius: 0 2px 2px 0;
    }

    .merob-card-source {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 10px;
      color: #8A8F98;
      margin-bottom: 6px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .merob-card-source .merob-score {
      margin-left: auto;
      color: #5E6AD2;
    }

    .merob-card-content {
      font-size: 12px;
      line-height: 1.5;
      color: #D4D4D8;
    }

    .merob-searching {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 24px;
      color: #8A8F98;
      font-size: 12px;
    }

    .merob-spinner {
      width: 14px;
      height: 14px;
      border: 2px solid rgba(255, 255, 255, 0.1);
      border-top-color: #5E6AD2;
      border-radius: 50%;
      animation: merob-spin 0.6s linear infinite;
    }

    @keyframes merob-spin {
      to { transform: rotate(360deg); }
    }

    .merob-error {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 12px;
      background: rgba(248, 81, 73, 0.05);
      border: 1px solid rgba(248, 81, 73, 0.15);
      border-radius: 8px;
      color: #F85149;
      font-size: 12px;
    }

    .merob-error code {
      background: rgba(0, 0, 0, 0.2);
      padding: 2px 6px;
      border-radius: 4px;
    }

    /* Minimized state */
    #merob-panel.minimized #merob-body { display: none; }
    #merob-panel.minimized {
      max-height: 52px;
      border-radius: 12px;
    }

    /* Launcher button */
    #merob-launcher {
      position: fixed;
      bottom: 20px;
      right: 20px;
      width: 48px;
      height: 48px;
      border-radius: 12px;
      background: rgba(17, 19, 20, 0.85);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.12);
      display: none;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow:
        0 8px 24px rgba(0, 0, 0, 0.4),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
      z-index: 99999;
      user-select: none;
      transition: all 0.2s ease;
    }

    #merob-launcher:hover {
      background: rgba(32, 34, 38, 0.9);
      border-color: rgba(255, 255, 255, 0.2);
      transform: translateY(-2px);
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
    }

    #merob-launcher:active {
      transform: translateY(0);
    }

    /* Extract progress toast */
    .merob-toast {
      position: fixed;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%) translateY(100px);
      background: #18191B;
      color: #F2F2F2;
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 8px;
      padding: 12px 20px;
      font-family: 'Inter', sans-serif;
      font-size: 13px;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 10px;
      z-index: 100000;
      box-shadow: 0 16px 48px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255,255,255,0.02);
      animation: merob-toast-in 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    @keyframes merob-toast-in {
      to { transform: translateX(-50%) translateY(0); }
    }

    .merob-toast.merob-toast-out {
      animation: merob-toast-out 0.3s ease forwards;
    }

    @keyframes merob-toast-out {
      to { transform: translateX(-50%) translateY(100px); opacity: 0; }
    }

    .merob-toast-success { border-color: rgba(63, 185, 80, 0.3); }
    .merob-toast-error { border-color: rgba(248, 81, 73, 0.3); }
  `;

  document.head.appendChild(style);
  document.body.appendChild(el);

  // Floating launcher to reopen the panel after it has been closed
  const launcher = document.createElement("div");
  launcher.id = "merob-launcher";
  launcher.title = "Open MerOb";
  launcher.innerHTML = `
    <svg width="26" height="26" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
      <circle cx="60" cy="60" r="10.5" fill="#5E6AD2"/>
      <circle cx="27" cy="36" r="6" fill="#5E6AD2" opacity="0.7"/>
      <circle cx="93" cy="36" r="6" fill="#5E6AD2" opacity="0.7"/>
      <circle cx="27" cy="84" r="6" fill="#5E6AD2" opacity="0.5"/>
      <circle cx="93" cy="84" r="6" fill="#5E6AD2" opacity="0.5"/>
      <line x1="60" y1="60" x2="27" y2="36" stroke="#8A8F98" stroke-width="1.5" opacity="0.55"/>
      <line x1="60" y1="60" x2="93" y2="36" stroke="#8A8F98" stroke-width="1.5" opacity="0.55"/>
      <line x1="60" y1="60" x2="27" y2="84" stroke="#8A8F98" stroke-width="1.5" opacity="0.4"/>
      <line x1="60" y1="60" x2="93" y2="84" stroke="#8A8F98" stroke-width="1.5" opacity="0.4"/>
    </svg>
  `;
  document.body.appendChild(launcher);

  return el;
}

// ======================
// TOAST NOTIFICATIONS
// ======================

function showToast(message, type = "success") {
  // Remove existing toasts
  document.querySelectorAll(".merob-toast").forEach(t => t.remove());

  const toast = document.createElement("div");
  toast.className = `merob-toast merob-toast-${type}`;
  toast.innerHTML = `
    <span>${type === "success" ? "✅" : "⚠️"}</span>
    <span>${message}</span>
  `;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("merob-toast-out");
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ======================
// SEARCH
// ======================

async function search(query) {
  const res = document.getElementById("merob-results");
  res.innerHTML = `
    <div class="merob-searching">
      <div class="merob-spinner"></div>
      <span>Searching memories…</span>
    </div>
  `;

  try {
    const r = await fetch(`${API}/memories/search?q=${encodeURIComponent(query)}&n=5`);
    const data = await r.json();

    if (!data.results || data.results.length === 0) {
      res.innerHTML = `
        <div class="merob-empty-hint">
          <span>No memories found for "${query}"</span>
        </div>
      `;
      document.getElementById("merob-inject-btn").style.display = "none";
      return;
    }

    res.innerHTML = "";
    data.results.forEach((item, i) => {
      const card = document.createElement("div");
      card.className = "merob-card";
      card.style.animationDelay = `${i * 0.05}s`;
      card.dataset.content = item.content;

      const sourceLabel = (item.file || item.source || "memory").replace(".md", "").replace(/_/g, " ");
      const scoreLabel = item.score ? `${Math.round(item.score * 100)}%` : "";

      card.innerHTML = `
        <div class="merob-card-source">
          <span>${sourceLabel}</span>
          ${scoreLabel ? `<span class="merob-score">${scoreLabel}</span>` : ""}
        </div>
        <div class="merob-card-content">${item.content}</div>
      `;
      card.addEventListener("click", () => card.classList.toggle("selected"));
      res.appendChild(card);
    });

    document.getElementById("merob-inject-btn").style.display = "flex";

  } catch (e) {
    res.innerHTML = `
      <div class="merob-error">
        <span>⚠</span>
        <span>Server unreachable. Run: <code>python run.py</code></span>
      </div>
    `;
  }
}

// ======================
// INJECT INTO PROMPT
// ======================

function injectIntoPrompt() {
  const selected = [...document.querySelectorAll(".merob-card.selected")];
  const cards    = selected.length > 0 ? selected : [...document.querySelectorAll(".merob-card")];

  if (cards.length === 0) return;

  const memories = cards.map(c => "- " + c.dataset.content).join("\\n");
  const context  = `[Personal memories]\\n${memories}\\n\\n`;

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

  showToast(`${cards.length} memor${cards.length > 1 ? "ies" : "y"} injected into prompt`);
}

// ======================
// EXTRACT AT END OF CONVERSATION
// ======================

async function extractConversation() {
  // Grab the page's visible text as a proxy for the conversation
  const msgs = [...document.querySelectorAll(
    '[data-message-author-role], .human-turn, .model-turn, ' +
    '.human, .assistant, [class*="message"]'
  )].map(el => el.innerText).filter(Boolean).join("\\n\\n");

  if (!msgs.trim()) {
    showToast("No conversation content found on this page.", "error");
    return;
  }

  const btn = document.getElementById("merob-extract-btn");
  const originalHTML = btn.innerHTML;
  btn.innerHTML = `<div class="merob-spinner" style="width:12px;height:12px;border-width:1.5px"></div> Extracting…`;
  btn.disabled = true;

  try {
    const r = await fetch(`${API}/extract`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation: msgs })
    });
    const data = await r.json();
    showToast(data.message || "Memories extracted successfully!");
  } catch (e) {
    showToast("Server unreachable. Run: python run.py", "error");
  } finally {
    btn.innerHTML = originalHTML;
    btn.disabled = false;
  }
}

// ======================
// DRAG (move the panel)
// ======================

function makeDraggable(panel) {
  const header = document.getElementById("merob-header");
  let dragging = false, ox = 0, oy = 0;

  header.addEventListener("mousedown", e => {
    // Don't drag when clicking buttons
    if (e.target.closest("button")) return;
    dragging = true;
    ox = e.clientX - panel.getBoundingClientRect().left;
    oy = e.clientY - panel.getBoundingClientRect().top;
    panel.style.transition = "none";
  });
  document.addEventListener("mousemove", e => {
    if (!dragging) return;
    panel.style.left   = (e.clientX - ox) + "px";
    panel.style.top    = (e.clientY - oy) + "px";
    panel.style.right  = "auto";
    panel.style.bottom = "auto";
  });
  document.addEventListener("mouseup", () => {
    if (dragging) {
      dragging = false;
      panel.style.transition = "";
    }
  });
}

// ======================
// INIT
// ======================

function init() {
  if (!getSite()) return;
  if (document.getElementById("merob-panel")) return;

  panel = createPanel();
  makeDraggable(panel);

  // Minimize / maximize
  document.getElementById("merob-toggle").addEventListener("click", () => {
    panel.classList.toggle("minimized");
    const toggleBtn = document.getElementById("merob-toggle");
    if (panel.classList.contains("minimized")) {
      toggleBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none">
        <path d="M4 8h8M8 4v8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      </svg>`;
      toggleBtn.title = "Expand";
    } else {
      toggleBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none">
        <path d="M4 8h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      </svg>`;
      toggleBtn.title = "Minimize";
    }
  });

  // Close → hide the panel and show the floating launcher to reopen it
  const launcher = document.getElementById("merob-launcher");
  document.getElementById("merob-close").addEventListener("click", () => {
    panel.style.display = "none";
    launcher.style.display = "flex";
  });
  launcher.addEventListener("click", () => {
    panel.classList.remove("minimized");
    const toggleBtn = document.getElementById("merob-toggle");
    toggleBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none">
      <path d="M4 8h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
    </svg>`;
    toggleBtn.title = "Minimize";
    panel.style.display = "flex";
    launcher.style.display = "none";
  });

  // Manual search
  document.getElementById("merob-search").addEventListener("input", e => {
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
      if (input && !input.dataset.merobListening) {
        input.dataset.merobListening = "1";
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
  document.getElementById("merob-inject-btn").addEventListener("click", injectIntoPrompt);

  // Extract
  document.getElementById("merob-extract-btn").addEventListener("click", extractConversation);
}

// Wait for the page to be ready (SPAs load late)
if (document.readyState === "complete") {
  init();
} else {
  window.addEventListener("load", init);
}
