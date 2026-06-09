const API = "http://localhost:8000";
const statusBadge = document.getElementById("status-badge");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const content = document.getElementById("content");

const CATEGORY_COLORS = [
  "#5E6AD2", "#26B5CE", "#3FB950", "#F85149", "#D29922", "#A371F7"
];

function setStatus(state) {
  statusDot.className = `dot ${state}`;
  if (state === 'connected') statusText.textContent = "Connected";
  else if (state === 'disconnected') statusText.textContent = "Offline";
  else statusText.textContent = "Connecting";
}

function renderStats(data) {
  const total = data.total || 0;
  const pending = data.pending_review || 0;
  const categories = data.by_file || {};

  const sortedCategories = Object.entries(categories)
    .filter(([, n]) => n > 0)
    .sort(([, a], [, b]) => b - a);

  content.innerHTML = `
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-label">Memories</div>
        <div class="stat-val">${total}</div>
      </div>
      <div class="stat-card" style="${pending > 0 ? 'border-color: rgba(248,81,73,0.3); background: rgba(248,81,73,0.03);' : ''}">
        <div class="stat-label">Pending</div>
        <div class="stat-val" style="color: ${pending > 0 ? 'var(--danger)' : 'var(--text)'}">${pending}</div>
      </div>
    </div>
    
    ${sortedCategories.length > 0 ? `
      <div class="section-title">Categories</div>
      <div class="categories">
        ${sortedCategories.slice(0, 6).map(([file, n], i) => `
          <div class="cat-row">
            <span class="cat-name">
              <span class="cat-dot" style="background: ${CATEGORY_COLORS[i % CATEGORY_COLORS.length]}"></span>
              ${file.replace(".md", "").replace(/_/g, " ")}
            </span>
            <span class="cat-count">${n}</span>
          </div>
        `).join("")}
      </div>
    ` : ""}
    
    <div style="display: flex; gap: 8px; margin-top: 4px;">
      <button class="btn primary" id="btn-open-vault">Open Vault</button>
      <button class="btn" id="btn-refresh">Refresh</button>
    </div>
  `;

  document.getElementById("btn-refresh")?.addEventListener("click", load);
  document.getElementById("btn-open-vault")?.addEventListener("click", async () => {
    try { await fetch(`${API}/open-vault`, { method: "POST" }); } catch (e) {}
  });
}

function renderError() {
  content.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">🔌</div>
      <div style="margin-bottom: 8px; color: var(--text);">Server unreachable</div>
      <code style="background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; font-family: monospace; color: var(--text-sec); border: 1px solid var(--border);">python run.py</code>
    </div>
    <button class="btn" id="btn-retry">Retry Connection</button>
  `;
  document.getElementById("btn-retry")?.addEventListener("click", load);
}

function renderLoading() {
  content.innerHTML = `
    <div class="stats-row">
      <div class="stat-card" style="height: 62px; background: rgba(255,255,255,0.02)"></div>
      <div class="stat-card" style="height: 62px; background: rgba(255,255,255,0.02)"></div>
    </div>
    <div style="height: 120px; background: rgba(255,255,255,0.02); border-radius: 8px;"></div>
  `;
}

async function load() {
  setStatus('connecting');
  renderLoading();
  
  try {
    const r = await fetch(`${API}/memories/count`);
    const data = await r.json();
    setStatus('connected');
    renderStats(data);
  } catch (e) {
    setStatus('disconnected');
    renderError();
  }
}

load();
