/* Founder OS Web UI */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

let state = {};
let currentView = "dashboard";
let chatHistory = JSON.parse(localStorage.getItem("fos_chat") || "[]");

const TITLES = {
  dashboard: "Dashboard",
  chat: "Chat with your agent",
  approvals: "Pending approvals",
  crm: "CRM & pipeline",
  goals: "Goals, tasks & reminders",
  memory: "Memory search",
  tools: "Tool catalog",
  activity: "Activity & traces",
  settings: "Settings",
};

async function api(path, opts = {}) {
  const r = await fetch("/api" + path, {
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
}

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s ?? "";
  return d.innerHTML;
}

function fmtMoney(n) {
  return "$" + Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function fmtTime(ts) {
  if (!ts) return "";
  const d = new Date(typeof ts === "number" && ts < 1e12 ? ts * 1000 : ts);
  return d.toLocaleString();
}

// ── Views ────────────────────────────────────────────────────────────────────

function renderDashboard() {
  const snap = state.snapshot || {};
  const crm = snap.crm || {};
  const fin = state.finance || {};
  const usage = state.usage || {};
  const about = state.about || {};
  const cfg = state.config || {};
  const pending = snap.approvals_pending || 0;
  const finPill = fin.set
    ? `<span class="pill ${fin.status === "healthy" ? "ok" : fin.status === "warning" ? "warn" : "info"}">${esc(fin.status)}</span>`
    : "";
  const runway = fin.set
    ? (fin.runway || (fin.runway_months != null ? fin.runway_months + " mo" : "—"))
    : null;
  const goals = (state.goals || []).slice(0, 5).map(g => `<li>${esc(g.title)}</li>`).join("")
    || "<li class='muted'>No active goals — set one in Chat.</li>";
  const approvalCell = pending > 0
    ? `<div class="spec-cell race-position-cell"><dt>Approvals waiting</dt><dd>${pending}</dd></div>`
    : `<div class="spec-cell"><dt>Approvals waiting</dt><dd>0</dd></div>`;

  return `
    <header class="hero-band-cinema">
      <p class="caption-uppercase">${esc(cfg.company_name || "Founder OS")}</p>
      <h2>Your operating system</h2>
      <p class="body-md">${esc(about.tagline || "Research, CRM, outreach, and execution — one agent, full control.")}</p>
      <div class="hero-actions">
        <button type="button" class="button-primary" data-goto="chat">Open chat</button>
        ${pending > 0 ? `<button type="button" class="button-outline-on-dark" data-goto="approvals">Review approvals</button>` : ""}
      </div>
    </header>
    <div class="dashboard-grid">
    <section class="driver-card span-12">
      <p class="caption-uppercase">At a glance</p>
      <dl class="stat-grid" style="margin-top:var(--space-sm)">
        <div class="spec-cell"><dt>Contacts</dt><dd>${crm.total_contacts || 0}</dd></div>
        <div class="spec-cell"><dt>Follow-ups due</dt><dd>${crm.followups_due || 0}</dd></div>
        <div class="spec-cell"><dt>Open tasks</dt><dd>${snap.tasks_open || 0}</dd></div>
        ${approvalCell}
        <div class="spec-cell"><dt>LLM calls today</dt><dd>${usage.llm_calls || 0}</dd></div>
        <div class="spec-cell"><dt>Est. cost</dt><dd class="small">$${usage.est_cost_usd || 0}</dd></div>
      </dl>
    </section>
    <section class="driver-card span-6">
      <p class="caption-uppercase">Runway ${finPill}</p>
      ${runway ? `<dl class="stat-grid" style="margin-top:var(--space-sm)">
        <div class="spec-cell"><dt>Cash</dt><dd class="small">${fmtMoney(fin.cash)}</dd></div>
        <div class="spec-cell"><dt>Monthly burn</dt><dd class="small">${fmtMoney(fin.monthly_burn)}</dd></div>
        <div class="spec-cell"><dt>MRR</dt><dd class="small">${fmtMoney(fin.mrr)}</dd></div>
        <div class="spec-cell"><dt>Runway</dt><dd class="small">${esc(runway)}</dd></div>
      </dl>` : `<p class="body-md" style="margin-top:var(--space-sm)">Share cash, burn, and MRR in Chat to track runway.</p>`}
    </section>
    <section class="driver-card span-6">
      <p class="caption-uppercase">Agent</p>
      <dl class="stat-grid" style="margin-top:var(--space-sm)">
        <div class="spec-cell"><dt>Tools available</dt><dd>${about.total_tools || "?"}</dd></div>
        <div class="spec-cell"><dt>Autonomy</dt><dd class="small">${esc(usage.autonomy_level || "?")}</dd></div>
      </dl>
    </section>
    <section class="driver-card span-6">
      <p class="caption-uppercase">Active goals</p>
      <ul class="list-plain" style="margin-top:var(--space-sm)">${goals}</ul>
    </section>
    <section class="livery-band span-6">
      <p class="caption-uppercase">Get started</p>
      <p class="display-lg">Message your agent</p>
      <p class="body-md" style="margin-top:var(--space-xs);max-width:36ch;opacity:0.9">Research, CRM, outreach, documents, calendar, and reminders — tools chosen automatically.</p>
      <button type="button" class="button-outline-on-dark" data-goto="chat" style="margin-top:var(--space-sm)">Start conversation</button>
    </section>
  </div>`;
}

function renderChat() {
  const msgs = chatHistory.map(m =>
    `<div class="msg ${m.role}">${esc(m.text)}</div>`
  ).join("");
  return `<div class="chat-wrap">
    <div class="chat-messages" id="chat-messages">${msgs || '<div class="msg system">Ask anything — research, CRM, goals, documents, outreach…</div>'}</div>
    <div class="chat-input-row">
      <textarea class="text-input-on-dark chat-input" id="chat-input" placeholder="Message your agent…" rows="2"></textarea>
      <button class="button-primary" id="chat-send">Send</button>
    </div>
    <div class="chat-toolbar">
      <label class="button-outline-on-dark button-sm upload-label">Upload file<input type="file" id="chat-file" hidden accept=".pdf,.docx,.txt,.md,.csv,.json"></label>
      <button type="button" class="button-outline-on-dark button-sm" id="chat-clear">Clear history</button>
    </div>
  </div>`;
}

function renderApprovals() {
  const appr = state.approvals || [];
  if (!appr.length) {
    return `<section class="driver-card"><p class="body-md">No pending approvals. Risky actions (send email, post to X, etc.) appear here for your decision.</p></section>`;
  }
  return `<section class="driver-card">${appr.map(a => `
    <div class="approval-block">
      <div class="approval-meta caption-uppercase"><span class="mono">#${a.id}</span> · ${esc(a.tool_name)}</div>
      <div class="approval-summary body-md">${esc(a.summary)}</div>
      <div class="approval-actions">
        <button type="button" class="button-primary button-sm" data-approve="${a.id}">Approve</button>
        <button type="button" class="button-outline-on-dark button-sm" data-reject="${a.id}">Reject</button>
      </div>
    </div>`).join("")}</section>`;
}

function renderCrm() {
  const contacts = state._crm?.contacts || [];
  const followups = state._crm?.followups_due || [];
  const pipeline = state._crm?.pipeline || {};
  const pipeRows = Object.entries(pipeline).map(([k, v]) =>
    `<div class="kv"><span class="k">${esc(k)}</span><span class="v">${v}</span></div>`
  ).join("") || "<p class='muted'>No pipeline data</p>";

  const rows = contacts.slice(0, 50).map(c => `<tr>
    <td>${esc(c.name)}</td><td>${esc(c.company || "—")}</td><td>${esc(c.role || "—")}</td>
    <td>${esc(c.status || "—")}</td><td class="muted">${esc(c.email || "")}</td></tr>`).join("");

  const fu = followups.map(c => `<li>${esc(c.name)} @ ${esc(c.company || "?")}</li>`).join("") || "<li class='muted'>None due</li>";

  return `<div class="dashboard-grid">
    <section class="driver-card span-4"><p class="caption-uppercase">Pipeline</p><div style="margin-top:var(--space-sm)">${pipeRows}</div></section>
    <section class="driver-card span-8"><p class="caption-uppercase">Follow-ups due</p><ul class="list-plain" style="margin-top:var(--space-sm)">${fu}</ul></section>
    <section class="band-light span-12">
      <p class="caption-uppercase" style="color:var(--color-muted)">Contacts (${contacts.length})</p>
      <div class="table-wrap"><table><thead><tr><th>Name</th><th>Company</th><th>Role</th><th>Status</th><th>Email</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="5" class="muted">No contacts yet — ask the agent to add leads.</td></tr>'}</tbody></table></div>
    </section>
  </div>`;
}

function renderGoals() {
  const g = state._goals || {};
  const goals = (g.active || []).map(x => `<li><strong>${esc(x.title)}</strong>${x.detail ? " — " + esc(x.detail) : ""}</li>`).join("") || "<li class='muted'>No active goals</li>";
  const tasks = (state.tasks || []).map(t => `<li>${esc(t.title)} <span class="muted">P${t.priority || 3}</span></li>`).join("") || "<li class='muted'>No open tasks</li>";
  const rems = (g.reminders || []).map(r => `<li>${esc(r.text)} <span class="muted">${esc(r.due_at)}</span></li>`).join("") || "<li class='muted'>No reminders</li>";
  const plans = (g.plans || []).map(p => `<li>${esc(p.goal)}</li>`).join("") || "<li class='muted'>No open plans</li>";

  return `<div class="dashboard-grid">
    <section class="driver-card span-6"><p class="caption-uppercase">Active goals</p><ul class="list-plain" style="margin-top:var(--space-sm)">${goals}</ul></section>
    <section class="driver-card span-6"><p class="caption-uppercase">Open tasks</p><ul class="list-plain" style="margin-top:var(--space-sm)">${tasks}</ul></section>
    <section class="driver-card span-6"><p class="caption-uppercase">Reminders</p><ul class="list-plain" style="margin-top:var(--space-sm)">${rems}</ul></section>
    <section class="driver-card span-6"><p class="caption-uppercase">Plans &amp; projects</p><ul class="list-plain" style="margin-top:var(--space-sm)">${plans}</ul></section>
  </div>`;
}

function renderMemory() {
  const results = state._memoryResults || [];
  const items = results.map(r => `<div class="memory-hit">
    <span class="badge-pill">${esc(r.collection)}</span>
    <p class="body-md" style="margin-top:var(--space-xxs);max-width:72ch">${esc(r.text)}</p></div>`).join("");
  return `<div class="search-row">
    <input type="search" class="text-input-on-dark" id="memory-q" placeholder="Search conversations, research, notes, documents…" value="${esc(state._memoryQ || "")}">
    <button class="button-primary" id="memory-search">Search</button>
  </div>
  <div id="memory-results">${items || '<p class="body-md">Enter a query to search vector memory.</p>'}</div>`;
}

function renderTools() {
  const t = state._tools || {};
  const rows = (t.tools || []).map(x => `<div class="tool-row">
    <div class="name">${esc(x.name)}${x.requires_approval ? ' <span class="badge-pill">approval</span>' : ""}</div>
    <div class="cat">${esc(x.category)}</div>
    <div class="desc">${esc(x.description)}</div></div>`).join("");
  return `<p class="body-md" style="margin-bottom:var(--space-xs);max-width:60ch">${t.total || 0} tools · ${Object.keys(t.by_category || {}).length} categories. Tool-RAG retrieves the most relevant set per message.</p>
  <div class="tool-list">${rows}</div>`;
}

function renderActivity() {
  const traces = state.traces || [];
  const actions = state.actions || [];
  const tr = traces.map(t => `<div class="activity-row">
    <div><span class="mono">${esc(t.actor)}</span> — ${esc(t.message)}</div>
    <div class="meta">${esc((t.tools || []).join(", ") || "no tools")} · ${t.duration_s}s</div></div>`).join("") || "<p class='muted'>No turns yet today.</p>";
  const act = actions.map(a => `<div class="activity-row">
    <div class="mono">${esc(a.tool_name)}</div>
    <div class="meta">${esc(a.actor)} · ${esc((a.created_at || "").slice(0, 16))}</div></div>`).join("") || "<p class='muted'>No actions logged.</p>";
  return `<div class="dashboard-grid">
    <section class="driver-card span-6"><p class="caption-uppercase">Recent turns</p><div style="margin-top:var(--space-sm)">${tr}</div></section>
    <section class="driver-card span-6"><p class="caption-uppercase">Action log</p><div style="margin-top:var(--space-sm)">${act}</div></section>
  </div>`;
}

function renderSettings() {
  const c = state.config || {};
  const pauseBtn = c.agent_paused
    ? `<button type="button" class="button-primary" id="toggle-pause" style="margin-top:var(--space-sm)">Resume agent</button>`
    : `<button type="button" class="button-outline-on-dark" id="toggle-pause" style="margin-top:var(--space-sm)">Pause agent</button>`;
  return `<div class="dashboard-grid">
    <section class="driver-card span-4">
      <p class="caption-uppercase">Identity</p>
      <dl class="stat-grid" style="margin-top:var(--space-sm)">
        <div class="spec-cell"><dt>Name</dt><dd class="small">${esc(c.my_name)}</dd></div>
        <div class="spec-cell"><dt>Company</dt><dd class="small">${esc(c.company_name)}</dd></div>
      </dl>
    </section>
    <section class="driver-card span-4">
      <p class="caption-uppercase">Agent control</p>
      <dl class="stat-grid" style="margin-top:var(--space-sm)">
        <div class="spec-cell"><dt>Autonomy</dt><dd class="small">${esc(c.autonomy_level)}</dd></div>
        <div class="spec-cell"><dt>Auto-approve</dt><dd class="small">${c.auto_approve ? "On" : "Off"}</dd></div>
        <div class="spec-cell"><dt>Paused</dt><dd class="small">${c.agent_paused ? "Yes" : "No"}</dd></div>
      </dl>
      ${pauseBtn}
    </section>
    <section class="driver-card span-4">
      <p class="caption-uppercase">Channels</p>
      <dl class="stat-grid" style="margin-top:var(--space-sm)">
        <div class="spec-cell"><dt>Web UI</dt><dd class="small">${c.web_ui_enabled ? "On" : "Off"}</dd></div>
        <div class="spec-cell"><dt>Telegram</dt><dd class="small">${c.telegram_enabled ? "On" : "Off"}</dd></div>
        <div class="spec-cell"><dt>Port</dt><dd class="small">${c.dashboard_port}</dd></div>
      </dl>
    </section>
    <section class="driver-card span-12">
      <p class="caption-uppercase">Configuration</p>
      <p class="body-md" style="margin-top:var(--space-sm);max-width:52ch">Edit <code class="mono">.env</code> for API keys, autonomy, and integrations. Restart the app to apply changes.</p>
    </section>
  </div>`;
}

// ── Navigation ───────────────────────────────────────────────────────────────

async function loadViewData(view) {
  if (view === "crm") state._crm = await api("/crm/contacts");
  if (view === "goals") state._goals = await api("/goals");
  if (view === "tools") state._tools = await api("/tools");
}

function goView(view) {
  currentView = view;
  $$(".nav button").forEach(b => b.classList.toggle("is-active", b.dataset.view === view));
  $("#view-title").textContent = TITLES[view] || view;
  render();
  loadViewData(view).then(render).catch(console.error);
}

function render() {
  const fns = {
    dashboard: renderDashboard, chat: renderChat, approvals: renderApprovals,
    crm: renderCrm, goals: renderGoals, memory: renderMemory,
    tools: renderTools, activity: renderActivity, settings: renderSettings,
  };
  $("#content").innerHTML = (fns[currentView] || renderDashboard)();
  bindViewEvents();
  if (currentView === "chat") {
    const el = $("#chat-messages");
    if (el) el.scrollTop = el.scrollHeight;
  }
}

function bindViewEvents() {
  $("#chat-send")?.addEventListener("click", sendChat);
  $("#chat-input")?.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); }
  });
  $("#chat-clear")?.addEventListener("click", () => {
    chatHistory = [];
    localStorage.setItem("fos_chat", "[]");
    render();
  });
  $("#chat-file")?.addEventListener("change", uploadFile);
  $$("[data-approve]").forEach(b => b.addEventListener("click", () => decideApproval(b.dataset.approve, true)));
  $$("[data-reject]").forEach(b => b.addEventListener("click", () => decideApproval(b.dataset.reject, false)));
  $("#memory-search")?.addEventListener("click", searchMemory);
  $("#memory-q")?.addEventListener("keydown", e => { if (e.key === "Enter") searchMemory(); });
  $("#toggle-pause")?.addEventListener("click", togglePause);
  $$("[data-goto]").forEach(b => b.addEventListener("click", () => goView(b.dataset.goto)));
}

async function sendChat() {
  const input = $("#chat-input");
  const text = (input?.value || "").trim();
  if (!text) return;
  input.value = "";
  chatHistory.push({ role: "user", text });
  localStorage.setItem("fos_chat", JSON.stringify(chatHistory));
  render();
  const btn = $("#chat-send");
  if (btn) { btn.disabled = true; btn.textContent = "…"; }
  try {
    const res = await api("/chat", { method: "POST", body: JSON.stringify({ message: text }) });
    chatHistory.push({ role: "agent", text: res.reply || "(no response)" });
    localStorage.setItem("fos_chat", JSON.stringify(chatHistory));
    if (res.new_approvals?.length) {
      state.approvals = res.pending_approvals;
      updateBadges();
    }
  } catch (e) {
    chatHistory.push({ role: "system", text: "Error: " + e.message });
  }
  if (btn) { btn.disabled = false; btn.textContent = "Send"; }
  render();
}

async function uploadFile(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  chatHistory.push({ role: "user", text: `📎 Uploaded: ${file.name}` });
  render();
  try {
    const r = await fetch("/api/upload", { method: "POST", body: fd });
    const res = await r.json();
    if (!r.ok) throw new Error(res.error);
    chatHistory.push({ role: "agent", text: res.reply });
  } catch (err) {
    chatHistory.push({ role: "system", text: "Upload failed: " + err.message });
  }
  localStorage.setItem("fos_chat", JSON.stringify(chatHistory));
  e.target.value = "";
  render();
}

async function decideApproval(id, approve) {
  try {
    const res = await api(`/approvals/${id}/${approve ? "approve" : "reject"}`, { method: "POST" });
    chatHistory.push({ role: "system", text: res.result });
    localStorage.setItem("fos_chat", JSON.stringify(chatHistory));
    await refresh();
    if (currentView === "approvals") render();
  } catch (e) { alert(e.message); }
}

async function searchMemory() {
  const q = $("#memory-q")?.value?.trim();
  state._memoryQ = q;
  if (!q) return;
  const res = await api("/memory/search?q=" + encodeURIComponent(q));
  state._memoryResults = res.results;
  render();
}

async function togglePause() {
  const paused = !(state.config?.agent_paused);
  await api("/agent/pause", { method: "POST", body: JSON.stringify({ paused }) });
  await refresh();
  render();
}

function updateBadges() {
  const n = (state.approvals || []).length;
  const nb = $("#nav-approval-badge");
  if (nb) { nb.textContent = n; nb.hidden = !n; }
  const unr = state.unread_notifications || 0;
  const nb2 = $("#notif-badge");
  if (nb2) { nb2.textContent = unr; nb2.hidden = !unr; }
}

function updateStatus() {
  const dot = $("#status-dot");
  const txt = $("#status-text");
  const c = state.config || {};
  if (c.agent_paused) {
    dot?.classList.add("paused"); dot?.classList.remove("ok");
    if (txt) txt.textContent = "Agent paused";
  } else {
    dot?.classList.add("ok"); dot?.classList.remove("paused");
    if (txt) txt.textContent = "Online";
  }
  const sub = $("#brand-sub");
  if (sub) sub.textContent = c.company_name || "Founder OS";
}

async function refresh() {
  state = await api("/state");
  updateBadges();
  updateStatus();
}

function renderNotifications() {
  const items = state.notifications || [];
  $("#notif-list").innerHTML = items.length ? items.map(n => `
    <div class="notif-item ${n.read ? "" : "unread"}">
      <div class="title">${esc(n.title)}</div>
      <div class="body">${esc(n.body)}</div>
      <div class="muted" style="font-size:11px;margin-top:4px">${fmtTime(n.ts)}</div>
    </div>`).join("") : "<p class='muted'>No notifications yet.</p>";
}

// ── Init ─────────────────────────────────────────────────────────────────────

$$(".nav button").forEach(b => b.addEventListener("click", () => goView(b.dataset.view)));
$("#btn-refresh")?.addEventListener("click", () => refresh().then(render));
const notifDialog = $("#notif-drawer");
$("#btn-notifications")?.addEventListener("click", () => {
  renderNotifications();
  notifDialog?.showModal();
});
notifDialog?.addEventListener("click", (e) => {
  if (e.target === notifDialog) notifDialog.close();
});
$("#notif-read-all")?.addEventListener("click", async () => {
  await api("/notifications/read-all", { method: "POST" });
  await refresh();
  renderNotifications();
  updateBadges();
});

refresh().then(() => { render(); setInterval(() => refresh().then(updateBadges).then(updateStatus), 30000); });
