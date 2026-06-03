const API = "http://localhost:8000";
const statusEl = document.getElementById("status");
const statsEl  = document.getElementById("stats");

async function load() {
  try {
    const r    = await fetch(`${API}/memories/count`);
    const data = await r.json();

    statusEl.textContent = "✓ Serveur connecté";
    statusEl.className   = "ok";

    const pendingClass = data.pending_review > 0 ? "stat-value pending" : "stat-value";

    statsEl.innerHTML = `
      <div class="stat-row">
        <span class="stat-label">Total mémoires</span>
        <span class="stat-value">${data.total}</span>
      </div>
      <div class="stat-row">
        <span class="stat-label">En attente</span>
        <span class="${pendingClass}">${data.pending_review}</span>
      </div>
      <div class="by-file">
        ${Object.entries(data.by_file)
          .filter(([, n]) => n > 0)
          .map(([f, n]) => `
            <div class="by-file-row">
              <span>${f.replace(".md", "")}</span>
              <span>${n}</span>
            </div>`)
          .join("")}
      </div>
    `;

  } catch (e) {
    statusEl.textContent = "⚠ Serveur inaccessible — lance uvicorn server:app --port 8000";
    statusEl.className   = "err";
  }
}

load();
