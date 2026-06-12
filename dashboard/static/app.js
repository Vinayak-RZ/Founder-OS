/* Nawab OS Web UI */

const APP_NAME = "Nawab OS";
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

function loadSelectedSpecialist() {
  const stored = localStorage.getItem("fos_selected_specialist");
  if (stored !== null) return stored;
  const legacy = localStorage.getItem("fos_selected_agent");
  if (legacy && legacy !== "supervisor") return legacy;
  return "";
}

const DEFAULT_SPECIALISTS = [
  { id: "pulse", label: "Pulse", role: "aggregator", tool_count: 0, brief: "Operating pulse across parallel projects" },
  { id: "outreach", label: "Outreach", role: "outreach", tool_count: 0, brief: "Outreach drafts and CRM pipeline" },
  { id: "leads", label: "Leads", role: "leads", tool_count: 0, brief: "Lead lists and contact priorities" },
  { id: "market", label: "Market intel", role: "research", tool_count: 0, brief: "Industry and competitor intelligence" },
  { id: "vault", label: "Vault", role: "knowledge", tool_count: 0, brief: "Knowledge vault librarian" },
];

const RAG_MODES = [
  { id: "auto", label: "Auto", hint: "Agent picks retrieval" },
  { id: "hybrid", label: "Hybrid RAG", hint: "Dense + BM25 fusion" },
  { id: "graphrag", label: "GraphRAG", hint: "Knowledge graph communities" },
  { id: "vault", label: "Vault", hint: "World knowledge vault" },
  { id: "documents", label: "Documents", hint: "Ingested document store" },
];

let state = {
  live: {},
  selectedSpecialist: loadSelectedSpecialist(),
  ragMode: localStorage.getItem("fos_rag_mode") || "auto",
  activeWorldId: localStorage.getItem("fos_active_world") || "root",
  agentsTab: localStorage.getItem("fos_agents_tab") || "runs",
  expandedRunId: null,
  ui: {
    worldCreateOpen: false,
    crmFormOpen: false,
    goalsFormOpen: false,
    reminderFormOpen: false,
    vaultFacet: null,
    vaultDocForm: null,
    vaultDocEdit: null,
  },
  _worldTemplates: null,
  _operations: {},
};
state._syncingLinkIds = new Set();
let currentView = "dashboard";

function readJsonStorage(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (e) {
    console.warn(`[storage] corrupt ${key}, resetting`, e);
    localStorage.removeItem(key);
    return fallback;
  }
}

let chatHistory = readJsonStorage("fos_chat", []);
let livePollTimer = null;
let memoryGraphTab = "graph";
let worldGraphTab = "hierarchy";
let lastLiveActive = false;

const TITLES = {
  dashboard: "Control center",
  chat: "Ask agent",
  agents: "Agent fleet",
  world: "Worlds",
  approvals: "Approvals",
  crm: "CRM & pipeline",
  goals: "Goals & tasks",
  memory: "Memory",
  tools: "Tools",
  activity: "Activity",
  settings: "Settings",
};

const CRM_STATUSES = ["prospect", "contacted", "replied", "meeting", "won", "lost", "nurture"];

const CHART_COLORS = ["#f75440", "#00666b", "#03904a", "#051f13", "#5a403c", "#8f706b", "#e3beb8"];

async function apiUpload(path, formData, method = "POST") {
  const r = await fetch("/api" + path, { method, body: formData, credentials: "same-origin" });
  const data = await r.json().catch(() => ({}));
  if (r.status === 401 && data.pin_required) {
    showPinGate();
    throw new Error("Enter your PIN to continue");
  }
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
}

async function api(path, opts = {}) {
  const ctrl = new AbortController();
  const ms = opts.timeoutMs ?? 30000;
  const timer = setTimeout(() => ctrl.abort(), ms);
  const { timeoutMs: _t, headers, signal, ...fetchOpts } = opts;
  try {
    const r = await fetch("/api" + path, {
      ...fetchOpts,
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(headers || {}) },
      signal: signal || ctrl.signal,
    });
    const data = await r.json().catch(() => ({}));
    if (r.status === 401 && data.pin_required) {
      showPinGate();
      throw new Error("Enter your PIN to continue");
    }
    if (!r.ok) throw new Error(data.error || r.statusText);
    return data;
  } catch (e) {
    if (e.name === "AbortError") throw new Error("Request timed out — is the server running?");
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

function isLinkSyncing(linkId) {
  return state._syncingLinkIds.has(String(linkId));
}

function renderOpsStack() {
  const host = document.getElementById("ops-stack");
  if (!host) return;
  const now = Date.now();
  const items = Object.values(state._operations || {})
    .filter(o => o.status === "running" || (o.finishedAt && now - o.finishedAt < 8000))
    .slice(0, 5);
  if (!items.length) {
    host.innerHTML = "";
    host.hidden = true;
    return;
  }
  host.hidden = false;
  host.innerHTML = items.map(o => {
    const pct = Math.round((o.progress || 0) * 100);
    const cls = o.status === "running" ? "is-running" : (o.status === "error" ? "is-error" : "is-done");
    const statusLabel = o.status === "running" ? "Working" : (o.status === "error" ? "Failed" : "Done");
    return `<div class="ops-card ${cls}" data-op-id="${esc(o.id)}">
      <div class="ops-card__head">
        <span class="ops-card__title">${esc(o.title)}</span>
        <span class="ops-card__status">${statusLabel}</span>
      </div>
      <p class="ops-card__detail">${esc(o.detail || "")}</p>
      ${o.status === "running" ? `<div class="ops-card__bar" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><span style="width:${pct}%"></span></div>` : ""}
    </div>`;
  }).join("");
}

async function runGithubSyncJob(jobId, title, meta = {}) {
  const opId = jobId;
  state._operations[opId] = {
    id: opId,
    title,
    detail: "Scanning repository…",
    progress: 0,
    status: "running",
  };
  if (meta.linkId != null) state._syncingLinkIds.add(String(meta.linkId));
  renderOpsStack();
  if (meta.worldId && currentView === "world") render();

  try {
    while (true) {
      const batch = await api(`/sync-jobs/${encodeURIComponent(jobId)}/batch`, {
        method: "POST",
        body: JSON.stringify({ batch_size: 8 }),
        timeoutMs: 180000,
      });
      const op = state._operations[opId];
      if (op) {
        op.progress = batch.progress || 0;
        op.detail = batch.message || `${batch.imported || 0} files imported`;
        op.status = batch.status === "failed" ? "error" : (batch.done ? "done" : "running");
      }
      renderOpsStack();
      if (batch.done) break;
    }
  } catch (e) {
    const op = state._operations[opId];
    if (op) {
      op.status = "error";
      op.detail = e.message || "Sync failed";
      op.finishedAt = Date.now();
    }
    renderOpsStack();
    throw e;
  } finally {
    const op = state._operations[opId];
    if (op && !op.finishedAt) op.finishedAt = Date.now();
    if (meta.linkId != null) state._syncingLinkIds.delete(String(meta.linkId));
    renderOpsStack();
    try {
      await refresh();
      if (meta.worldId) await loadWorldVault(meta.worldId);
      if (currentView === "world") render();
      updateBadges();
    } catch (_) { /* ignore refresh errors */ }
    setTimeout(() => {
      delete state._operations[opId];
      renderOpsStack();
    }, 8000);
  }
}

async function resumeActiveSyncJobs(worldId) {
  const res = await api(`/worlds/${encodeURIComponent(worldId)}/sync-jobs`).catch(() => ({ jobs: [] }));
  for (const j of res.jobs || []) {
    if (!j?.id || state._operations[j.id]) continue;
    runGithubSyncJob(j.id, `Syncing ${j.full_name}`, { worldId, linkId: j.link_id }).catch(console.error);
  }
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

function ownerLabel() {
  const c = state.config || {};
  return c.my_name ? `${c.my_name}'s ${APP_NAME}` : APP_NAME;
}

function currentWorldId() {
  return $("#world-select")?.value || state.activeWorldId || "root";
}

function activeWorldLabel() {
  const tree = state.worlds || state._worldFull?.worlds || {};
  const id = currentWorldId();
  if (id === "root") return tree.root?.name || "Main world";
  const child = (tree.children || []).find(c => c.id === id);
  return child?.name || id;
}

function setActiveWorld(id) {
  state.activeWorldId = id || "root";
  localStorage.setItem("fos_active_world", state.activeWorldId);
  populateWorldSelect();
}

function supervisorMeta(agents) {
  const sup = agents?.supervisor || {};
  return {
    id: "supervisor",
    label: "Supervisor",
    role: "aggregator",
    tool_count: agents?.total_tools,
    brief: sup.role || "Orchestrates specialists — picks who to run when routing is Auto",
  };
}

function listSpecialists(agents) {
  const specs = agents?.specialists || [];
  const list = specs.length ? specs : DEFAULT_SPECIALISTS;
  return list.map(s => ({ ...s, label: s.label || s.id }));
}

function currentSpecialistId() {
  const raw = $("#specialist-select-agents")?.value
    ?? state.selectedSpecialist
    ?? "";
  return raw === "auto" ? "" : (raw || "");
}

function currentRagMode() {
  return $("#rag-mode-select")?.value || state.ragMode || "auto";
}

function isDirectSpecialist() {
  return !!currentSpecialistId();
}

function populateSpecialistSelect() {
  const specs = listSpecialists(state._agents || {});
  let current = state.selectedSpecialist ?? "";
  if (current && !specs.some(s => s.id === current)) current = "";
  state.selectedSpecialist = current;

  const specOpts = specs.map(s =>
    `<option value="${esc(s.id)}">${esc(s.label)}</option>`
  ).join("");
  const html = `<option value="">Auto — supervisor decides</option>${specOpts}`;

  const el = $("#specialist-select-agents");
  if (el) {
    el.innerHTML = html;
    el.value = current;
  }
}

function renderRagModeSelect(id = "rag-mode-select") {
  const mode = state.ragMode || "auto";
  const opts = RAG_MODES.map(m =>
    `<option value="${esc(m.id)}" title="${esc(m.hint)}">${esc(m.label)}</option>`
  ).join("");
  return `<label class="chat-control">
    <span class="caption-uppercase">Retrieval</span>
    <select id="${esc(id)}" class="world-select agent-select" aria-label="RAG mode">${opts}</select>
  </label>`;
}

function routingLabel(agents) {
  const specId = currentSpecialistId();
  if (!specId) return "Supervisor · auto-route";
  const spec = listSpecialists(agents || state._agents || {}).find(s => s.id === specId);
  return `Supervisor → ${spec?.label || specId}`;
}

function routingMeta(agents) {
  const pool = state._agents || agents || {};
  const specId = currentSpecialistId();
  if (specId) {
    return listSpecialists(pool).find(s => s.id === specId)
      || { id: specId, label: specId, role: "specialist" };
  }
  return supervisorMeta(pool);
}

function populateWorldSelect() {
  const sel = $("#world-select");
  if (!sel) return;
  const tree = state.worlds || state._worldFull?.worlds || {};
  const root = tree.root;
  const children = tree.children || [];
  const childOpts = children.map(c =>
    `<option value="${esc(c.id)}">${esc(c.name)} · ${esc(c.kind || "project")}</option>`
  ).join("");
  sel.innerHTML = `
    <optgroup label="Main">
      <option value="root">${esc(root?.name || "Main world")} — all context</option>
    </optgroup>
    ${children.length ? `<optgroup label="Sub-worlds">${childOpts}</optgroup>` : ""}`;
  const current = currentWorldId();
  if ([...sel.options].some(o => o.value === current)) sel.value = current;
  else sel.value = "root";
}

function renderLiveFlow(events, emptyLabel = "Waiting for activity…") {
  if (!events?.length) {
    return `<p class="body-md muted">${esc(emptyLabel)}</p>`;
  }
  return `<div class="tool-flow">${events.map((e, i) => {
    const arrow = i > 0 ? '<span class="tool-flow-arrow" aria-hidden="true">→</span>' : "";
    if (e.type === "phase") {
      return `${arrow}<span class="tool-flow-node">${esc(e.label)}</span>`;
    }
    const cls = e.decision === "approve" ? " is-approve" : e.decision === "deny" ? " is-deny" : "";
    return `${arrow}<span class="tool-flow-node${cls}">${esc(e.name || e.label)}</span>`;
  }).join("")}</div>`;
}

function renderLivePanel(live, id = "live-panel") {
  const active = live?.active;
  return `<section class="live-panel${active ? " is-active" : ""}" id="${id}" aria-live="polite">
    <p class="caption-uppercase">Live operation</p>
    <p class="live-phase" id="${id}-phase">${esc(live?.phase || "Idle — send a message or delegate a task")}</p>
    <div id="${id}-flow">${renderLiveFlow(live?.events || [])}</div>
    ${active && live.elapsed_s ? `<p class="world-meta">${live.elapsed_s}s elapsed · ${esc(live.actor)}</p>` : ""}
  </section>`;
}

function agentBusy(live, agentId) {
  const actor = live?.active ? String(live.actor || "") : "";
  const id = String(agentId || "");
  if (id === "supervisor") return actor === "user";
  return actor === `subagent:${id}` || (id && actor.includes(id));
}

const AGENT_ROLES = {
  aggregator: { label: "Aggregator", cls: "agent-role--aggregator", avatar: "agent-avatar--aggregator" },
  outreach: { label: "Outreach", cls: "agent-role--outreach", avatar: "agent-avatar--outreach" },
  leads: { label: "Leads", cls: "agent-role--leads", avatar: "agent-avatar--leads" },
  research: { label: "Intel", cls: "agent-role--research", avatar: "agent-avatar--research" },
  knowledge: { label: "Vault", cls: "agent-role--vault", avatar: "agent-avatar--knowledge" },
};

const AGENT_INITIALS = {
  supervisor: "SV",
  pulse: "PL",
  outreach: "OR",
  leads: "LD",
  market: "MK",
  vault: "VL",
};

function agentRoleBadge(role) {
  const m = AGENT_ROLES[role] || { label: role || "Specialist", cls: "" };
  return `<span class="agent-role-badge ${m.cls}">${esc(m.label)}</span>`;
}

function agentAvatar(agentId, role) {
  const m = AGENT_ROLES[role] || AGENT_ROLES.aggregator;
  const initials = AGENT_INITIALS[agentId] || (agentId || "??").slice(0, 2).toUpperCase();
  return `<span class="agent-avatar ${m.avatar || "agent-avatar--aggregator"}" aria-hidden="true">${esc(initials)}</span>`;
}

function lastRunForAgent(agentId, runs) {
  const hit = (runs || []).find(r => r.agent === agentId);
  if (!hit?.ts) return "";
  const d = new Date(typeof hit.ts === "number" && hit.ts < 1e12 ? hit.ts * 1000 : hit.ts);
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function collectAgentRuns() {
  const fromApi = state._agentRunsApi || [];
  const local = readJsonStorage("fos_agent_runs", []);
  const merged = [...local];
  for (const r of fromApi) {
    if (!merged.some(m => m.id === r.id)) merged.push({ ...r, source: "trace" });
  }
  merged.sort((a, b) => (b.ts || 0) - (a.ts || 0));
  return merged.slice(0, 50);
}

function persistAgentRun(record) {
  const rows = readJsonStorage("fos_agent_runs", []);
  rows.unshift(record);
  localStorage.setItem("fos_agent_runs", JSON.stringify(rows.slice(0, 50)));
}

function renderFleetAutoCard(live) {
  const isSel = !currentSpecialistId();
  return `<button type="button" class="fleet-card fleet-card--auto${isSel ? " is-selected" : ""}" data-select-specialist="" aria-pressed="${isSel}">
    ${isSel ? `<span class="fleet-card__active-label">Routing</span>` : ""}
    <div class="fleet-card__top">
      <span class="agent-avatar agent-avatar--aggregator" aria-hidden="true">AU</span>
      <span class="fleet-card__status" title="Supervisor routes"></span>
    </div>
    <div class="fleet-card__name">Auto</div>
    <span class="agent-role-badge agent-role--aggregator">Supervisor picks</span>
    <div class="fleet-card__meta"><span>Default routing</span></div>
  </button>`;
}

function renderSupervisorBanner(agents, live) {
  const sup = supervisorMeta(agents);
  const busy = agentBusy(live, "supervisor");
  return `<div class="supervisor-banner driver-card">
    <div class="agent-card-title-row">
      ${agentAvatar("supervisor", sup.role)}
      <div>
        <h2 class="title-md">${esc(sup.label)} <span class="supervisor-main-tag">Main agent</span></h2>
        <p class="world-meta">${esc((sup.brief || "").slice(0, 140))}</p>
      </div>
    </div>
    <span class="agent-status ${busy ? "busy" : "ready"}">${busy ? "Working" : "Always on"}</span>
  </div>`;
}

function renderFleetCard(a, live, sel, runs) {
  const isBusy = agentBusy(live, a.id);
  const isSel = sel === a.id;
  const last = lastRunForAgent(a.id, runs);
  return `<button type="button" class="fleet-card${isBusy ? " is-busy" : ""}${isSel ? " is-selected" : ""}" data-select-specialist="${esc(a.id)}" aria-pressed="${isSel}">
    ${isSel ? `<span class="fleet-card__active-label">Direct</span>` : ""}
    <div class="fleet-card__top">
      ${agentAvatar(a.id, a.role)}
      <span class="fleet-card__status ${isBusy ? "is-busy" : ""}" title="${isBusy ? "Working" : "Idle"}"></span>
    </div>
    <div class="fleet-card__name">${esc(a.label)}</div>
    ${a.role ? agentRoleBadge(a.role) : ""}
    <p class="fleet-card__brief">${esc((a.brief || "").slice(0, 72))}</p>
    <div class="fleet-card__meta">
      <span>${a.tool_count ?? "—"} tools</span>
      ${last ? `<span>${esc(last)}</span>` : ""}
    </div>
  </button>`;
}

function renderAgentCards(agents, live, selectable = false) {
  const specs = listSpecialists(agents);
  const sel = currentSpecialistId();
  const runs = collectAgentRuns();
  if (!selectable) {
    return `<div class="agent-grid">${specs.map(a => {
      const card = { ...a, label: a.label || a.id };
      const busy = agentBusy(live, a.id);
      return `<article class="agent-card${busy ? " is-busy" : ""}">
        <div class="agent-card-head">${renderFleetCardInner(card, live, runs)}</div>
      </article>`;
    }).join("")}</div>`;
  }
  return `<div class="fleet-rail">${renderFleetAutoCard(live)}${specs.map(a =>
    renderFleetCard(a, live, sel, runs)
  ).join("")}</div>`;
}

function renderFleetCardInner(a, live, runs) {
  const isBusy = agentBusy(live, a.id);
  const last = lastRunForAgent(a.id, runs);
  return `
    <div class="agent-card-title-row">
      ${agentAvatar(a.id, a.role)}
      <div><h3>${esc(a.label)}</h3>${a.role ? agentRoleBadge(a.role) : ""}</div>
    </div>
    <span class="agent-status ${isBusy ? "busy" : "ready"}">${isBusy ? "Working" : "Ready"}</span>
    <p class="agent-meta">${a.tool_count ?? 0} tools${last ? ` · ${esc(last)}` : ""}</p>`;
}

function renderAgentRunsTable(runs) {
  if (!runs.length) {
    return `<div class="empty-state"><p class="title-sm">No specialist runs yet</p></div>`;
  }
  return `<div class="table-wrap"><table class="data-table">
    <thead><tr><th>Time</th><th>Agent</th><th>Task</th><th>Duration</th><th>Tools</th><th></th></tr></thead>
    <tbody>${runs.map(r => {
      const ts = r.ts ? fmtTime(r.ts) : "—";
      const tools = (r.tools || []).slice(0, 4).join(", ");
      const expanded = state.expandedRunId === r.id;
      return `<tr class="data-row${expanded ? " is-expanded" : ""}" data-run-id="${esc(r.id)}">
        <td class="mono muted">${esc(ts)}</td>
        <td><span class="fleet-inline-badge">${esc((r.agent || "").toUpperCase())}</span></td>
        <td class="task-cell">${esc((r.task || "").slice(0, 120))}</td>
        <td class="mono">${r.duration_s ? `${r.duration_s}s` : "—"}</td>
        <td class="muted">${esc(tools || "—")}</td>
        <td><button type="button" class="button-tertiary-text button-sm" data-toggle-run="${esc(r.id)}">${expanded ? "Hide" : "View"}</button></td>
      </tr>
      ${expanded ? `<tr class="data-row-detail"><td colspan="6"><pre class="run-result mono">${esc(r.result || "No output recorded")}</pre></td></tr>` : ""}`;
    }).join("")}</tbody>
  </table></div>`;
}

function renderAgentsToolsPanel() {
  const t = state._tools || {};
  const byCat = t.by_category || {};
  const cats = Object.entries(byCat).sort((a, b) => b[1] - a[1]);
  return `<div class="console-split">
    <div class="driver-card">${cats.map(([cat, n]) =>
      `<div class="kv-row"><span class="k">${esc(cat)}</span><span class="v">${n}</span></div>`
    ).join("") || "<p class='muted'>No tools loaded</p>"}</div>
    <div class="driver-card tool-list-compact">${(t.tools || []).slice(0, 24).map(x =>
      `<div class="tool-chip">${esc(x.name)}${x.requires_approval ? '<span class="badge-pill">approval</span>' : ""}</div>`
    ).join("")}</div>
  </div>`;
}

function renderAgentsCrmPanel() {
  const crm = state._crm || {};
  const pipeline = crm.pipeline || {};
  const contacts = crm.contacts || [];
  const followups = crm.followups_due || [];
  const pipeRows = Object.entries(pipeline).map(([k, v]) =>
    `<div class="kv-row"><span class="k">${esc(k)}</span><span class="v">${v}</span></div>`
  ).join("");
  const fu = followups.slice(0, 8).map(c =>
    `<li>${esc(c.name)} <span class="muted">${esc(c.company || "")}</span></li>`
  ).join("") || "<li class='muted'>None due</li>";
  const recent = contacts.slice(0, 10).map(c =>
    `<tr><td>${esc(c.name)}</td><td>${esc(c.company || "—")}</td><td>${esc(c.status || "—")}</td></tr>`
  ).join("");
  return `<div class="console-split">
    <section class="driver-card"><p class="caption-uppercase">Pipeline</p>${pipeRows || "<p class='muted'>Empty</p>"}
      <p class="caption-uppercase" style="margin-top:var(--space-sm)">Follow-ups due</p><ul class="list-plain">${fu}</ul></section>
    <section class="driver-card"><p class="caption-uppercase">Contacts (${contacts.length})</p>
      <div class="table-wrap"><table class="data-table"><thead><tr><th>Name</th><th>Company</th><th>Status</th></tr></thead>
      <tbody>${recent || "<tr><td colspan='3' class='muted'>No contacts</td></tr>"}</tbody></table></div>
      <button type="button" class="button-outline-on-dark button-sm" data-goto="crm" style="margin-top:var(--space-xs)">Open CRM</button>
    </section>
  </div>`;
}

function renderAgentsVaultPanel() {
  const vault = state._worldVault?.vault || state._worldVault || {};
  const facets = vault.folders || vault.facets || [];
  const q = state._agentsVaultQ || "";
  return `<div class="console-split">
    <section class="driver-card">
      <p class="caption-uppercase">Vault · ${esc(activeWorldLabel())}</p>
      <div class="vault-facet-grid" style="margin-top:var(--space-xs)">${facets.map(f =>
        `<div class="vault-facet-card"><div class="vault-facet-head"><h4>${esc(f.domain_label || f.label || f.folder || "")}</h4><span class="badge-pill">${f.file_count ?? 0} files</span></div></div>`
      ).join("") || "<p class='muted'>Select a sub-world or link a repo in Worlds</p>"}</div>
      <button type="button" class="button-outline-on-dark button-sm" data-goto="world" style="margin-top:var(--space-sm)">Manage vault</button>
    </section>
    <section class="driver-card">
      <div class="search-row">
        <input type="search" class="text-input-on-dark" id="agents-vault-q" placeholder="Search vault…" value="${esc(q)}">
        <button type="button" class="button-primary button-sm" id="agents-vault-search">Search</button>
      </div>
      <pre class="run-result mono" id="agents-vault-results" hidden></pre>
    </section>
  </div>`;
}

function renderAgentsTabPanel() {
  const tab = state.agentsTab || "runs";
  const runs = collectAgentRuns();
  if (tab === "runs") return renderAgentRunsTable(runs);
  if (tab === "live") {
    const live = state.live || {};
    return `${renderLivePanel(live, "agents-tab-live")}
      <div id="graph-runtime-agents-tab" class="graph-canvas graph-canvas--compact" style="margin-top:var(--space-sm)"></div>`;
  }
  if (tab === "tools") return renderAgentsToolsPanel();
  if (tab === "crm") return renderAgentsCrmPanel();
  if (tab === "vault") return renderAgentsVaultPanel();
  return "";
}

function renderGraphOrPlaceholder(containerId, graphData, opts = {}, emptyMessage = "Nothing to visualize yet.") {
  if (!window.FOSGraph) return null;
  const el = document.getElementById(containerId);
  if (!el) return null;
  let ph = el.parentElement?.querySelector(`[data-graph-placeholder-for="${containerId}"]`);
  if (!ph) {
    ph = document.createElement("p");
    ph.className = "graph-placeholder body-md muted";
    ph.dataset.graphPlaceholderFor = containerId;
    el.insertAdjacentElement("afterend", ph);
  }
  const nodes = graphData?.nodes || [];
  const edges = graphData?.edges || [];
  const onlyEmpty = nodes.length === 1 && nodes[0]?.data?.type === "empty";
  const hasGraph = (nodes.length + edges.length) > 0 && !onlyEmpty;
  const cy = hasGraph ? FOSGraph.render(containerId, graphData, opts) : null;
  if (!cy) {
    el.classList.add("is-empty");
    ph.hidden = false;
    ph.textContent = emptyMessage;
  } else {
    el.classList.remove("is-empty");
    ph.hidden = true;
  }
  return cy;
}

function buildVaultGraph(vault, world) {
  if (vault?.nodes && vault?.edges) return vault;
  const v = vault?.vault || vault || {};
  const w = world || {};
  const nodes = [];
  const edges = [];
  const wid = w.id || v.world_id || "world";
  const worldNid = `vault-world:${wid}`;
  nodes.push({ data: { id: worldNid, label: (w.name || "World").slice(0, 36), type: "world_root", world_id: wid } });

  const facets = v.facets || v.folders || [];
  facets.forEach((facet) => {
    const fid = facet.id || facet.folder || "slot";
    const fnid = `vault-facet:${wid}:${fid}`;
    const label = `${facet.label || facet.folder || "Folder"} (${facet.file_count || 0})`;
    nodes.push({ data: { id: fnid, label: label.slice(0, 40), type: "vault_facet", facet_id: fid, folder: facet.folder } });
    edges.push({ data: { source: worldNid, target: fnid, label: "folder" } });
    (facet.documents || []).slice(0, 14).forEach((doc, i) => {
      const did = `vault-doc:${doc.id || i}`;
      nodes.push({
        data: {
          id: did,
          label: (doc.title || doc.filename || "Document").slice(0, 36),
          type: "vault_file",
          doc_id: doc.id,
          facet_id: fid,
          source: doc.source_type || "upload",
        },
      });
      edges.push({ data: { source: fnid, target: did, label: "doc" } });
    });
    (facet.files || []).slice(0, 8).forEach((file, i) => {
      const dnid = `vault-disk:${wid}:${fid}:${i}`;
      nodes.push({
        data: {
          id: dnid,
          label: (file.name || file.relative || "file").slice(0, 32),
          type: "vault_file",
          path: file.relative,
          facet_id: fid,
          source: "disk",
        },
      });
      edges.push({ data: { source: fnid, target: dnid, label: "disk" } });
    });
  });
  (v.github_repos || []).slice(0, 10).forEach((repo) => {
    const rid = `gh-repo:${repo.id}`;
    nodes.push({
      data: {
        id: rid,
        label: (repo.full_name || "repo").split("/").pop().slice(0, 28),
        type: "vault_repo",
        link_id: repo.id,
        repo: repo.full_name,
      },
    });
    edges.push({ data: { source: worldNid, target: rid, label: "github" } });
  });
  if (nodes.length <= 1) {
    nodes.push({ data: { id: "vault-empty", label: "Add docs or link GitHub", type: "empty" } });
    edges.push({ data: { source: worldNid, target: "vault-empty", label: "start" } });
  }
  return { nodes, edges };
}

function vaultGraphForWorld(world) {
  const vault = state._worldVault?.vault || state._worldVault || {};
  if (state._vaultGraph?.nodes?.length) return state._vaultGraph;
  return buildVaultGraph(vault, world);
}

function drawGraphs() {
  if (!window.FOSGraph) return;
  if (currentView === "dashboard" && state._runtimeGraph) {
    renderGraphOrPlaceholder(
      "graph-runtime-dash",
      state._runtimeGraph,
      { layout: { name: "breadthfirst", directed: true, padding: 20 } },
      "Runtime graph appears when an agent is active.",
    );
  }
  if (currentView === "agents" && state._runtimeGraph) {
    const el = state.agentsTab === "live" ? "graph-runtime-agents-tab" : "graph-runtime-agents";
    if (document.getElementById(el)) {
      renderGraphOrPlaceholder(el, state._runtimeGraph, {}, "Runtime graph appears when an agent is active.");
    }
  }
  if (currentView === "chat" && state._runtimeGraph && document.getElementById("graph-runtime-chat")) {
    renderGraphOrPlaceholder(
      "graph-runtime-chat",
      state._runtimeGraph,
      { layout: { name: "breadthfirst", directed: true, padding: 16 } },
      "Runtime graph appears when an agent is active.",
    );
  }
  if (currentView === "world") {
    const selected = worldById(inspectorWorldId());
    if (worldGraphTab === "vault" && !isRootWorld(selected)) {
      renderGraphOrPlaceholder(
        "graph-world",
        vaultGraphForWorld(selected),
        {
          layout: FOSGraph.HIERARCHY_LAYOUT,
          onSelect: (d) => {
            if (d.facet_id) {
              state.ui = { ...(state.ui || {}), vaultFacet: d.facet_id };
              render();
              drawGraphs();
            }
          },
        },
        "No files yet — add documents or link a GitHub repo in the knowledge panel below.",
      );
    } else {
      const graph = worldGraphTab === "ecosystem"
        ? state._worldGraph
        : (state._worldHierarchyGraph || state._worldGraph);
      if (graph) {
        renderGraphOrPlaceholder(
          "graph-world",
          graph,
          {
            layout: worldGraphTab === "hierarchy" ? FOSGraph.HIERARCHY_LAYOUT : FOSGraph.LAYOUT,
            onSelect: (d) => {
              if (d.world_id) selectInspectorWorld(d.world_id);
            },
          },
          "World map will appear once your hierarchy is loaded.",
        );
        window.FOSGraph?.highlightWorld("graph-world", inspectorWorldId(), currentWorldId());
      } else {
        renderGraphOrPlaceholder("graph-world", null, {}, "World map will appear once your hierarchy is loaded.");
      }
    }
    if (document.getElementById("graph-vault-inline")) {
      renderGraphOrPlaceholder(
        "graph-vault-inline",
        vaultGraphForWorld(selected),
        { layout: FOSGraph.HIERARCHY_LAYOUT },
        "Add documents or link GitHub to see your file map.",
      );
    }
  }
  if (currentView === "memory" && state._memoryGraph) {
    renderGraphOrPlaceholder(
      "graph-memory",
      state._memoryGraph,
      {
        onSelect: (d) => {
          const el = $("#graph-memory-detail");
          if (el) el.textContent = `${d.type}: ${d.label}`;
        },
      },
      "Memory graph fills in as you store knowledge and run agents.",
    );
  }
}

async function loadGraphData() {
  try {
    state._runtimeGraph = await api("/graph/runtime");
  } catch (_) { state._runtimeGraph = null; }
  if (currentView === "world" || currentView === "dashboard") {
    try {
      const w = currentView === "world" ? await api("/graph/world") : state._world;
      state._worldGraph = w?.graph || state._world?.graph;
      state._worldHierarchyGraph = w?.hierarchy_graph || state._worldHierarchyGraph;
      state._worldPreviews = w?.world_previews || state._worldPreviews || {};
      if (currentView === "world") state._worldFull = w;
    } catch (_) {}
  }
  if (currentView === "memory") {
    try {
      const m = await api("/graph/memory");
      state._memoryGraph = m.graph;
      state._memoryFull = m;
    } catch (_) {}
  }
}

function chartPanelNote(canvasId, message, show) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const panel = canvas.closest(".chart-panel");
  if (!panel) return;
  let note = panel.querySelector(".chart-empty");
  if (!note) {
    note = document.createElement("p");
    note.className = "chart-empty muted body-md";
    panel.appendChild(note);
  }
  note.textContent = message;
  note.hidden = !show;
  canvas.hidden = show;
}

function drawDashboardCharts() {
  const narrow = window.innerWidth < 640;
  const tools = state._world?.tools_by_category || state.about?.tools_by_category || {};
  const entries = Object.entries(tools).slice(0, narrow ? 5 : 8);
  if (entries.length && $("#chart-tools")) {
    chartPanelNote("chart-tools", "", false);
    FOSCharts.bar("chart-tools", entries.map(([k]) => k), entries.map(([, v]) => v), { colors: CHART_COLORS });
  } else {
    chartPanelNote("chart-tools", "No tool data yet.", true);
  }
  const crm = state.snapshot?.crm?.by_status || {};
  const segs = Object.entries(crm).filter(([, v]) => v > 0).map(([k, v]) => ({ label: k, value: v }));
  if (segs.length && $("#chart-crm")) {
    chartPanelNote("chart-crm", "", false);
    FOSCharts.donut("chart-crm", segs, { centerLabel: "contacts", colors: CHART_COLORS });
  } else {
    chartPanelNote("chart-crm", "No CRM contacts yet — add leads in Chat or CRM.", true);
  }
  const hist = [...(state.usage_history || [])].reverse();
  const points = hist.map(h => h.llm_calls || h.calls || 0);
  if (points.length && $("#chart-usage")) {
    chartPanelNote("chart-usage", "", false);
    FOSCharts.spark("chart-usage", points);
  } else {
    chartPanelNote("chart-usage", "No LLM usage in the last 7 days.", true);
  }
}

function updateLiveStrip(live) {
  const strip = $("#live-strip");
  const txt = $("#live-strip-text");
  if (!strip) return;
  const active = !!live?.active;
  if (active !== lastLiveActive) {
    FOSMotion?.pulseLiveStrip?.(active);
    lastLiveActive = active;
  }
  if (txt && active) txt.textContent = live.phase || "Agent working…";
}

function patchLiveUI(live) {
  state.live = live || {};
  updateLiveStrip(live);
  $$("[id$='-phase']").forEach(el => { el.textContent = live?.phase || "Idle"; });
  $$("[id$='-flow']").forEach(el => { el.innerHTML = renderLiveFlow(live?.events || []); });
  $$(".live-panel").forEach(el => el.classList.toggle("is-active", !!live?.active));
}

async function pollLive() {
  try {
    const live = await api("/live");
    patchLiveUI(live);
    if (["dashboard", "agents", "chat"].includes(currentView)) {
      state._runtimeGraph = await api("/graph/runtime").catch(() => state._runtimeGraph);
      if (window.FOSGraph) {
        if (currentView === "dashboard") FOSGraph.update("graph-runtime-dash", state._runtimeGraph);
        if (currentView === "agents") {
          const el = state.agentsTab === "live" ? "graph-runtime-agents-tab" : null;
          if (el && document.getElementById(el)) FOSGraph.update(el, state._runtimeGraph);
        }
        if (currentView === "chat" && document.getElementById("graph-runtime-chat")) {
          FOSGraph.update("graph-runtime-chat", state._runtimeGraph);
        }
      }
    }
  } catch (_) { /* ignore */ }
}

function startLivePoll() {
  stopLivePoll();
  pollLive();
  livePollTimer = setInterval(pollLive, 1500);
}

function stopLivePoll() {
  if (livePollTimer) { clearInterval(livePollTimer); livePollTimer = null; }
}

// ── Human operator UI ────────────────────────────────────────────────────────

function renderWorldCreateForm(formId = "world-create-form") {
  return `
    <form class="world-form human-form" id="${esc(formId)}">
      <div class="human-form__row">
        <label class="human-field"><span class="caption-uppercase">Name</span>
          <input class="text-input-on-dark" name="name" placeholder="e.g. Stamped Energy" required></label>
        <label class="human-field"><span class="caption-uppercase">Category</span>
          <select class="text-input-on-dark" name="kind" id="world-create-kind">
            <option value="project">Startup / venture</option>
            <option value="technical">Technical project</option>
            <option value="idea">Idea / exploration</option>
            <option value="research">Technical research</option>
          </select></label>
        <label class="human-field"><span class="caption-uppercase">Knowledge template</span>
          <select class="text-input-on-dark" name="template">
            <option value="startup">Startup — ICP, GTM, product, leads…</option>
            <option value="technical">Technical — architecture, stack, ADRs…</option>
            <option value="idea">Idea — hypothesis, research, next steps</option>
            <option value="research">Research — papers, synthesis, industry</option>
          </select></label>
      </div>
      <label class="human-field"><span class="caption-uppercase">Description</span>
        <input class="text-input-on-dark" name="description" placeholder="One-line summary"></label>
      <label class="human-field"><span class="caption-uppercase">Context for agents</span>
        <textarea class="text-input-on-dark" name="context" rows="3" placeholder="What should agents know when this world is active?"></textarea></label>
      <div class="human-form__row">
        <label class="human-field"><span class="caption-uppercase">Local docs path</span>
          <input class="text-input-on-dark" name="repo_path" placeholder="Optional: C:\\docs\\my-project"></label>
        <label class="human-field"><span class="caption-uppercase">GitHub repo</span>
          <input class="text-input-on-dark" name="github_repo" placeholder="Optional: owner/repo"></label>
      </div>
      <div class="human-form__actions">
        <button type="submit" class="button-primary button-sm">Create world</button>
        <button type="button" class="button-outline-on-dark button-sm" data-toggle-ui="worldCreateOpen">Cancel</button>
      </div>
    </form>`;
}

function renderOperatorPanel() {
  const cfg = state.config || {};
  const pending = state.snapshot?.approvals_pending || 0;
  const paused = cfg.agent_paused;
  return `
    <section class="driver-card span-12 operator-panel" aria-label="Direct actions">
      <div class="operator-panel__head">
        <div>
          <p class="section-eyebrow">You drive</p>
          <h3 class="title-sm">Direct controls</h3>
          <p class="body-md muted">Manage worlds, CRM, goals, and agent policy yourself. Chat is optional — use it when you want help.</p>
        </div>
        <div class="operator-panel__status">
          <span class="pill ${paused ? "warn" : "ok"}">${paused ? "Agent paused" : "Agent on standby"}</span>
          <span class="pill info">${esc(cfg.autonomy_level || "balanced")} autonomy</span>
        </div>
      </div>
      <div class="operator-grid">
        <button type="button" class="operator-card" data-operator="create-world">
          <span class="operator-card__title">New world</span>
          <span class="operator-card__desc">Add a venture, project, or idea</span>
        </button>
        <button type="button" class="operator-card" data-operator="add-contact">
          <span class="operator-card__title">Add contact</span>
          <span class="operator-card__desc">CRM lead or relationship</span>
        </button>
        <button type="button" class="operator-card" data-operator="add-goal">
          <span class="operator-card__title">New goal</span>
          <span class="operator-card__desc">Track an outcome you own</span>
        </button>
        <button type="button" class="operator-card" data-operator="add-reminder">
          <span class="operator-card__title">Reminder</span>
          <span class="operator-card__desc">Schedule a follow-up</span>
        </button>
        <button type="button" class="operator-card" data-operator="settings">
          <span class="operator-card__title">Agent policy</span>
          <span class="operator-card__desc">Autonomy &amp; approvals</span>
        </button>
        <button type="button" class="operator-card${pending ? " operator-card--alert" : ""}" data-operator="approvals">
          <span class="operator-card__title">Approvals${pending ? ` (${pending})` : ""}</span>
          <span class="operator-card__desc">Review before agents act</span>
        </button>
      </div>
    </section>`;
}

function openOperatorAction(action) {
  if (!state.ui) state.ui = {};
  if (action === "create-world") {
    state.ui.worldCreateOpen = true;
    if (currentView === "world") {
      render();
      requestAnimationFrame(() => document.getElementById("world-create-panel")?.scrollIntoView({ behavior: "smooth", block: "nearest" }));
    } else {
      goView("world");
      state._scrollWorldCreate = true;
    }
    return;
  }
  if (action === "add-contact") {
    state.ui.crmFormOpen = true;
    if (currentView === "crm") render();
    else goView("crm");
    return;
  }
  if (action === "add-goal") {
    state.ui.goalsFormOpen = true;
    if (currentView === "goals") render();
    else goView("goals");
    return;
  }
  if (action === "add-reminder") {
    state.ui.reminderFormOpen = true;
    if (currentView === "goals") render();
    else goView("goals");
    return;
  }
  if (action === "settings") goView("settings");
  if (action === "approvals") goView("approvals");
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
    || "<li class='muted'>No active goals — add one in Goals or use Direct controls.</li>";
  const approvalCell = pending > 0
    ? `<div class="spec-cell race-position-cell"><dt>Approvals</dt><dd>${pending}</dd></div>`
    : `<div class="spec-cell"><dt>Approvals</dt><dd>0</dd></div>`;
  const live = state.live || {};
  const agents = state._agents || {};

  return `
    <header class="command-header driver-card">
      <div>
        <p class="section-eyebrow">${esc(cfg.company_name || APP_NAME)}</p>
        <h2 class="title-md">${esc(ownerLabel())}</h2>
      </div>
      <div class="command-header__actions">
        <button type="button" class="button-primary button-sm" data-operator="create-world">New world</button>
        <button type="button" class="button-outline-on-dark button-sm" data-goto="crm">CRM</button>
        <button type="button" class="button-outline-on-dark button-sm" data-goto="goals">Goals</button>
        <button type="button" class="button-outline-on-dark button-sm" data-goto="chat">Ask agent</button>
        ${pending > 0 ? `<button type="button" class="button-outline-on-dark button-sm" data-goto="approvals">Approvals (${pending})</button>` : ""}
      </div>
    </header>
    <div class="dashboard-grid">
      ${renderOperatorPanel()}
      <section class="driver-card span-8">
        ${renderLivePanel(live)}
        <p class="caption-uppercase" style="margin-top:var(--space-md)">Runtime graph</p>
        <div id="graph-runtime-dash" class="graph-canvas graph-canvas--compact" style="margin-top:var(--space-xs)"></div>
      </section>
      <section class="driver-card span-4">
        <p class="caption-uppercase">World state</p>
        <p class="world-meta" style="margin-top:var(--space-xxs)">Updated ${esc(snap.ts || "now")}</p>
        <dl class="stat-grid" style="margin-top:var(--space-sm)">
          <div class="spec-cell"><dt>Tools</dt><dd>${about.total_tools || 0}</dd></div>
          <div class="spec-cell"><dt>Agents</dt><dd>${(agents.specialists?.length || 4) + 1}</dd></div>
          <div class="spec-cell"><dt>Contacts</dt><dd>${crm.total_contacts || 0}</dd></div>
          ${approvalCell}
        </dl>
      </section>
      <section class="driver-card span-4 chart-panel">
        <p class="caption-uppercase">Tools by category</p>
        <canvas id="chart-tools" role="img" aria-label="Bar chart of tools by category"></canvas>
      </section>
      <section class="driver-card span-4 chart-panel">
        <p class="caption-uppercase">CRM pipeline</p>
        <div class="donut-wrap"><canvas id="chart-crm" role="img" aria-label="CRM contacts by status"></canvas></div>
      </section>
      <section class="driver-card span-4 chart-panel">
        <p class="caption-uppercase">LLM usage (7d)</p>
        <canvas id="chart-usage" role="img" aria-label="LLM calls sparkline"></canvas>
      </section>
      <section class="driver-card span-8">
        <p class="caption-uppercase">Recent activity</p>
        <div class="activity-timeline">${(state.actions || []).slice(0, 8).map(a =>
          `<div class="activity-timeline__row"><span class="mono">${esc(a.tool_name)}</span><span class="muted">${esc((a.created_at || "").slice(11, 19))}</span></div>`
        ).join("") || "<p class='muted'>No tool actions yet</p>"}</div>
      </section>
      <section class="driver-card span-4">
        <p class="caption-uppercase">Specialist status</p>
        <div class="specialist-chips">${listSpecialists(agents).map(s =>
          `<span class="specialist-chip${agentBusy(live, s.id) ? " is-busy" : ""}">${esc(s.label)}</span>`
        ).join("")}</div>
        <button type="button" class="button-outline-on-dark button-sm" data-goto="agents" style="margin-top:var(--space-sm)">Open agents</button>
      </section>
      <section class="driver-card span-12">
        <p class="caption-uppercase">Agent fleet</p>
        <div style="margin-top:var(--space-sm)">${renderAgentCards(agents, live)}</div>
      </section>
      <section class="driver-card span-6">
        <p class="caption-uppercase">Runway ${finPill}</p>
        ${runway ? `<dl class="stat-grid" style="margin-top:var(--space-sm)">
          <div class="spec-cell"><dt>Cash</dt><dd class="small">${fmtMoney(fin.cash)}</dd></div>
          <div class="spec-cell"><dt>Burn</dt><dd class="small">${fmtMoney(fin.monthly_burn)}</dd></div>
          <div class="spec-cell"><dt>MRR</dt><dd class="small">${fmtMoney(fin.mrr)}</dd></div>
          <div class="spec-cell"><dt>Runway</dt><dd class="small">${esc(runway)}</dd></div>
        </dl>` : `<p class="body-md" style="margin-top:var(--space-sm)">Set cash, burn, and MRR in Settings or ask the agent to track runway.</p>`}
      </section>
      <section class="driver-card span-6">
        <p class="caption-uppercase">Active goals</p>
        <ul class="list-plain" style="margin-top:var(--space-sm)">${goals}</ul>
        <dl class="stat-grid" style="margin-top:var(--space-sm)">
          <div class="spec-cell"><dt>Tasks open</dt><dd>${snap.tasks_open || 0}</dd></div>
          <div class="spec-cell"><dt>LLM today</dt><dd class="small">${usage.llm_calls || 0}</dd></div>
        </dl>
      </section>
    </div>`;
}

function renderAgents() {
  const agents = state._agents || {};
  const live = state.live || agents.live || {};
  const meta = routingMeta(agents);
  const routeLabel = routingLabel(agents);
  const direct = isDirectSpecialist();
  const draft = state._delegateDraft || "";
  const runs = collectAgentRuns();
  const pending = (state.approvals || []).length;
  const busyCount = (agents.specialists || []).filter(s => agentBusy(live, s.id)).length;
  const skills = agents.skills || [];
  const tab = state.agentsTab || "runs";
  const hasResult = !!(state._delegateResult || "").trim();
  const actions = state._agentActions || [];

  return `<div class="agents-console">
    <header class="console-toolbar driver-card">
      <div class="console-kpis">
        <div class="console-kpi"><span class="console-kpi__val">${agents.specialists?.length || 5}</span><span class="console-kpi__lbl">Specialists</span></div>
        <div class="console-kpi"><span class="console-kpi__val">${busyCount || "0"}</span><span class="console-kpi__lbl">Active</span></div>
        <div class="console-kpi"><span class="console-kpi__val">${runs.length}</span><span class="console-kpi__lbl">Runs</span></div>
        <div class="console-kpi"><span class="console-kpi__val">${agents.total_tools || 0}</span><span class="console-kpi__lbl">Tools</span></div>
        <div class="console-kpi"><span class="console-kpi__val">${pending}</span><span class="console-kpi__lbl">Approvals</span></div>
      </div>
      <div class="console-toolbar__actions">
        <span class="badge-pill">${esc(activeWorldLabel())}</span>
        ${skills.map(s => `<span class="skill-chip${s.installed ? "" : " is-missing"}">${esc(s.name)}</span>`).join("")}
        <button type="button" class="button-outline-on-dark button-sm" data-goto="chat">Chat</button>
        <button type="button" class="button-outline-on-dark button-sm" data-goto="approvals"${pending ? "" : " disabled"}>Approvals${pending ? ` (${pending})` : ""}</button>
      </div>
    </header>

    ${renderSupervisorBanner(agents, live)}

    <section class="agent-picker-bar driver-card">
      <div class="agent-picker-bar__head">
        <div>
          <p class="caption-uppercase">Specialist routing</p>
          <p class="world-meta">Supervisor is always on — pick <strong>Auto</strong> or a specialist for direct tasks</p>
        </div>
        <label class="world-select-wrap agent-picker-bar__select">
          <span class="caption-uppercase">Dropdown</span>
          <select id="specialist-select-agents" class="world-select agent-select" aria-label="Specialist override"></select>
        </label>
        <span class="badge-pill agent-routing-badge">${esc(routeLabel)}</span>
      </div>
      <div class="agent-picker-bar__cards">${renderAgentCards(agents, live, true)}</div>
    </section>

    <div class="agents-workspace">
      <section class="task-composer driver-card">
        <div class="task-composer__head">
          <div class="agent-card-title-row">
            ${agentAvatar(direct ? meta.id : "supervisor", direct ? meta.role : "aggregator")}
            <div>
              <h2 class="title-md">${direct ? esc(meta.label) : "Supervisor"}</h2>
              <p class="world-meta">${direct ? esc((meta.brief || "").slice(0, 100)) : "Auto-route — supervisor will delegate to the best specialist"}</p>
            </div>
          </div>
          <span class="agent-status ${agentBusy(live, direct ? meta.id : "supervisor") ? "busy" : "ready"}">${esc(routeLabel)}</span>
        </div>
        <textarea class="text-input-on-dark task-composer__input" id="delegate-selected" rows="3" placeholder="${direct ? `Task for ${esc(meta.label)}…` : "Message supervisor…"}">${esc(draft)}</textarea>
        <div class="task-composer__foot">
          <button type="button" class="button-primary" id="delegate-selected-btn">${direct ? `Run ${esc(meta.label)}` : "Send to supervisor"}</button>
          <span class="world-meta mono">${esc(activeWorldLabel())}</span>
        </div>
        ${hasResult ? `<pre class="delegate-result mono" id="delegate-result-selected">${esc(state._delegateResult || "")}</pre>` : ""}
      </section>

      <aside class="agents-rail driver-card">
        ${renderLivePanel(live, "agents-live-panel")}
        <p class="caption-uppercase" style="margin-top:var(--space-sm)">Recent actions</p>
        <div class="action-feed">${actions.slice(0, 8).map(a =>
          `<div class="action-feed__item"><span class="mono">${esc(a.tool_name)}</span><span class="muted">${esc((a.created_at || "").slice(11, 16))}</span></div>`
        ).join("") || "<p class='muted'>No actions yet</p>"}</div>
      </aside>
    </div>

    <section class="driver-card agents-panel">
      <div class="workspace-tabs">
        <button type="button" class="workspace-tab${tab === "runs" ? " is-active" : ""}" data-agents-tab="runs">Run history</button>
        <button type="button" class="workspace-tab${tab === "live" ? " is-active" : ""}" data-agents-tab="live">Live runtime</button>
        <button type="button" class="workspace-tab${tab === "tools" ? " is-active" : ""}" data-agents-tab="tools">Tools</button>
        <button type="button" class="workspace-tab${tab === "crm" ? " is-active" : ""}" data-agents-tab="crm">CRM</button>
        <button type="button" class="workspace-tab${tab === "vault" ? " is-active" : ""}" data-agents-tab="vault">Vault</button>
      </div>
      <div class="agents-tab-body">${renderAgentsTabPanel()}</div>
    </section>
  </div>`;
}

const WORLD_KINDS = {
  root: { label: "Main", cls: "world-kind--root" },
  project: { label: "Startup", cls: "world-kind--project" },
  startup: { label: "Startup", cls: "world-kind--project" },
  technical: { label: "Technical", cls: "world-kind--research" },
  idea: { label: "Idea", cls: "world-kind--idea" },
  research: { label: "Research", cls: "world-kind--research" },
};

function worldKindMeta(kind) {
  return WORLD_KINDS[kind] || WORLD_KINDS.project;
}

function worldKindBadge(kind) {
  const m = worldKindMeta(kind || "project");
  return `<span class="world-kind-badge ${m.cls}">${esc(m.label)}</span>`;
}

function worldTreeData() {
  return state._worldFull?.worlds || state.worlds || {};
}

function worldById(id) {
  const tree = worldTreeData();
  const wid = id || "root";
  if (wid === "root" || wid === tree.root?.id) return tree.root || null;
  return (tree.children || []).find(c => c.id === wid) || null;
}

function inspectorWorldId() {
  return state.inspectorWorldId || currentWorldId() || "root";
}

async function loadWorldVault(worldId) {
  if (!worldId || worldId === "root") {
    state._worldVault = null;
    state._vaultGraph = null;
    return;
  }
  try {
    const res = await api(`/worlds/${encodeURIComponent(worldId)}/vault`);
    state._worldVault = res.vault || null;
    state._vaultGraph = res.vault_graph || null;
  } catch (_) {
    state._worldVault = null;
    state._vaultGraph = null;
  }
}

function selectInspectorWorld(id) {
  state.inspectorWorldId = id || "root";
  if (currentView === "world") {
    state._motionSkipOnce = true;
    loadWorldVault(id).then(() => {
      render();
      drawGraphs();
      FOSMotion?.flashElement?.($("#world-inspector"));
      window.FOSGraph?.highlightWorld("graph-world", inspectorWorldId(), currentWorldId());
    });
  }
}

function renderWorldTreeNav(root, children, inspectId, activeId) {
  const rootId = root?.id || "root";
  const rootBtn = `
    <button type="button" class="world-tree-item is-root${inspectId === rootId ? " is-inspect" : ""}${activeId === rootId ? " is-active" : ""}"
      data-inspect-world="${esc(rootId)}">
      <span class="dot" aria-hidden="true"></span>
      <span class="meta">
        <span class="name">${esc(root?.name || "Main world")}</span>
        <span class="sub">Top-level · all ventures</span>
      </span>
    </button>`;
  const childBtns = children.map(c => `
    <button type="button" class="world-tree-item kind-${esc(c.kind || "project")}${inspectId === c.id ? " is-inspect" : ""}${activeId === c.id ? " is-active" : ""}"
      data-inspect-world="${esc(c.id)}">
      <span class="dot" aria-hidden="true"></span>
      <span class="meta">
        <span class="name">${esc(c.name)}</span>
        <span class="sub">${esc(c.kind || "project")} · ${esc((c.description || "No description").slice(0, 42))}</span>
      </span>
    </button>`).join("");
  return `
    <nav class="world-tree-nav" aria-label="World hierarchy">
      ${rootBtn}
      ${children.length ? `<div class="world-tree-children">${childBtns}</div>` : ""}
    </nav>`;
}

function renderWorldInspector(w, snap) {
  if (!w) return `<p class="body-md muted">Select a world to inspect its context.</p>`;
  const id = w.id || "root";
  const isRoot = id === "root";
  const kind = isRoot ? "root" : (w.kind || "project");
  const activeId = currentWorldId();
  const previews = state._worldPreviews || state._worldFull?.world_previews || {};
  const preview = previews[id] || "";
  const crm = snap?.crm || {};
  const fin = snap?.finance || {};
  const editing = state.worldEditing === id;

  if (editing) {
    return `
      <form class="world-edit-form" id="world-edit-form" data-world-id="${esc(id)}">
        <div class="world-inspector-title">
          <h2>Edit ${esc(w.name)}</h2>
          ${worldKindBadge(kind)}
        </div>
        ${!isRoot ? `
          <label>Name<input class="text-input-on-dark" name="name" value="${esc(w.name || "")}" required></label>
          <label>Category
            <select class="text-input-on-dark" name="kind" id="world-edit-kind">
              <option value="project"${w.kind === "project" ? " selected" : ""}>Startup / venture</option>
              <option value="idea"${w.kind === "idea" ? " selected" : ""}>Idea</option>
              <option value="research"${w.kind === "research" ? " selected" : ""}>Technical research</option>
              <option value="technical"${w.kind === "technical" ? " selected" : ""}>Technical project</option>
            </select>
          </label>
          <label>Knowledge template
            <select class="text-input-on-dark" name="template" id="world-edit-template">
              ${(state._worldTemplates || []).map(t =>
                `<option value="${esc(t.id)}"${(w.template || "") === t.id ? " selected" : ""}>${esc(t.label)}</option>`
              ).join("") || `<option value="startup"${(w.template || "startup") === "startup" ? " selected" : ""}>Startup / venture</option>`}
            </select>
          </label>` : `
          <label>Name<input class="text-input-on-dark" name="name" value="${esc(w.name || "")}"></label>`}
        <label>Description<textarea class="text-input-on-dark" name="description" rows="2">${esc(w.description || "")}</textarea></label>
        <label>Agent context<textarea class="text-input-on-dark" name="context" rows="5">${esc(w.context || "")}</textarea></label>
        <div class="world-inspector-actions">
          <button type="submit" class="button-primary button-sm">Save</button>
          <button type="button" class="button-tertiary-text button-sm" data-cancel-edit>Cancel</button>
        </div>
      </form>`;
  }

  const globalFacts = isRoot ? [
    ["Contacts", crm.total_contacts || 0],
    ["Follow-ups", crm.followups_due || 0],
    ["Open tasks", snap?.tasks_open || 0],
    ["Approvals", snap?.approvals_pending || 0],
  ] : [];
  if (isRoot && fin?.set) {
    globalFacts.push(["Runway", fin.runway_months != null ? `${fin.runway_months} mo` : "—"]);
  }

  const childIndex = isRoot ? (worldTreeData().children || []) : [];
  const goals = (snap?.goals_active || []).slice(0, 5);

  return `
    <div class="world-inspector-title">
      <div>
        <h2>${esc(w.name)}</h2>
        <p class="world-meta">id: ${esc(id)}${w.updated_at ? ` · updated ${esc(w.updated_at)}` : ""}</p>
      </div>
      ${worldKindBadge(kind)}
    </div>
    ${activeId === id
      ? `<p class="world-meta" style="color:var(--color-primary)">● Active for chat &amp; agents</p>`
      : `<p class="world-meta">Not active — switch from the top bar or below</p>`}
    <div class="world-inspector-section">
      <h4>Description</h4>
      <p>${esc(w.description || "No description yet.")}</p>
    </div>
    <div class="world-inspector-section">
      <h4>Agent context</h4>
      <p>${esc(w.context || "No focused context — add what the agent should know in this world.")}</p>
    </div>
    ${globalFacts.length ? `
      <div class="world-inspector-section">
        <h4>Global snapshot</h4>
        <div class="world-inspector-facts">${globalFacts.map(([k, v]) =>
          `<div class="world-inspector-fact"><span class="k">${esc(k)}</span><span class="v">${esc(String(v))}</span></div>`
        ).join("")}</div>
      </div>` : ""}
    ${isRoot && childIndex.length ? `
      <div class="world-inspector-section">
        <h4>Sub-worlds indexed (${childIndex.length})</h4>
        <div class="world-inspector-facts">${childIndex.map(c =>
          `<div class="world-inspector-fact"><span class="k">${esc(c.name)}</span><span class="v">${esc(c.kind || "project")}</span></div>`
        ).join("")}</div>
      </div>` : ""}
    ${!isRoot ? `
      <div class="world-inspector-section">
        <h4>Template</h4>
        <p class="body-md">${esc(w.template || kind)} — facet folders on disk under <code class="mono">data/knowledge/</code></p>
        ${w.github_repo ? `<p class="world-meta">GitHub: ${esc(w.github_repo)}</p>` : ""}
        ${w.repo_path ? `<p class="world-meta">Repo: ${esc(w.repo_path)}</p>` : ""}
      </div>` : ""}
    ${!isRoot && worldTreeData().root ? `
      <div class="world-inspector-section">
        <h4>Parent</h4>
        <p class="body-md">${esc(worldTreeData().root.name)} <span class="world-meta">(main world)</span></p>
      </div>` : ""}
    ${goals.length && isRoot ? `
      <div class="world-inspector-section">
        <h4>Active goals</h4>
        <p class="body-md">${goals.map(g => esc(typeof g === "string" ? g : g.title || g)).join(" · ")}</p>
      </div>` : ""}
    <div class="world-inspector-section">
      <h4>What the agent sees</h4>
      <pre class="world-context-preview">${esc(preview || "Preview loads when graph data is fetched…")}</pre>
    </div>
    <div class="world-inspector-actions">
      <button type="button" class="button-primary button-sm" data-use-world="${esc(id)}">Use in chat</button>
      <button type="button" class="button-outline-on-dark button-sm" data-set-active-world="${esc(id)}">Set active</button>
      <button type="button" class="button-tertiary-text button-sm" data-edit-world="${esc(id)}">Edit</button>
      ${!isRoot ? `<button type="button" class="button-tertiary-text button-sm" data-delete-world="${esc(id)}">Delete</button>` : ""}
    </div>`;
}

function renderVaultDocForm(w, facets, facetId) {
  const editing = state.ui?.vaultDocEdit;
  const fid = facetId || facets[0]?.id || facets[0]?.folder || "docs";
  const facet = facets.find(f => (f.id || f.folder) === fid) || facets[0] || { label: fid, id: fid };
  const title = editing ? (editing.title || "") : "";
  const desc = editing ? (editing.description || "") : "";
  const editId = editing?.id || "";
  return `
    <form class="human-form vault-doc-form" id="vault-doc-form" data-world-id="${esc(w.id)}" data-facet-id="${esc(fid)}">
      ${editId ? `<input type="hidden" name="doc_id" value="${editId}">` : ""}
      <div class="human-form__row">
        <label class="human-field"><span class="caption-uppercase">Category slot</span>
          <select class="text-input-on-dark" name="facet_id" id="vault-doc-facet">
            ${facets.map(f => {
              const id = f.id || f.folder;
              return `<option value="${esc(id)}"${id === fid ? " selected" : ""}>${esc(f.label)}</option>`;
            }).join("")}
          </select></label>
        <label class="human-field"><span class="caption-uppercase">Title</span>
          <input class="text-input-on-dark" name="title" required placeholder="e.g. Current ICP" value="${esc(title)}"></label>
      </div>
      <label class="human-field"><span class="caption-uppercase">Description (indexed for search)</span>
        <textarea class="text-input-on-dark" name="description" rows="3" placeholder="Short summary agents use to find this doc. Full content goes to ${esc(vaultStorageLabel())}.">${esc(desc)}</textarea></label>
      ${editId ? `
      <label class="human-field"><span class="caption-uppercase">Document body (markdown)</span>
        <textarea class="text-input-on-dark" name="content" id="vault-doc-content" rows="8" placeholder="Loading…"></textarea></label>` : `
      <label class="human-field"><span class="caption-uppercase">Upload file</span>
        <input type="file" name="file" accept=".pdf,.docx,.txt,.md,.markdown,.csv,.json"></label>
      <label class="human-field"><span class="caption-uppercase">Or paste markdown</span>
        <textarea class="text-input-on-dark" name="content" rows="6" placeholder="# ICP\n\nTarget: …"></textarea></label>`}
      <div class="human-form__actions">
        <button type="submit" class="button-primary button-sm">${editId ? "Update document" : "Add document"}</button>
        <button type="button" class="button-outline-on-dark button-sm" data-vault-cancel-doc>Cancel</button>
      </div>
      <p class="world-meta">Slot: <strong>${esc(facet.label)}</strong> · Full files in ${esc(vaultStorageLabel())}; only title + description in vector index.</p>
    </form>`;
}

function vaultStorageLabel() {
  const b = state._worldVault?.storage_backend || state._worldVault?.vault?.storage_backend;
  return b === "s3" ? "S3" : "local object storage";
}

function renderGithubReposPanel(w, vault) {
  const status = state._githubStatus || {};
  const connected = !!status.connected;
  const oauthOk = !!status.oauth_configured;
  const linked = vault.github_repos || [];
  const ghRepos = state._githubRepos || [];
  const pickOpts = ghRepos.map(r =>
    `<option value="${esc(r.full_name)}">${esc(r.full_name)}${r.private ? " (private)" : ""}</option>`
  ).join("");
  const linkedRows = linked.map(r => {
    const syncing = isLinkSyncing(r.id);
    return `
    <div class="github-repo-row">
      <div>
        <strong class="mono">${esc(r.full_name)}</strong>
        ${syncing ? `<span class="sync-badge">Syncing</span>` : ""}
        <span class="world-meta">${r.file_count || 0} files synced${r.synced_at ? ` · ${esc(r.synced_at)}` : ""}</span>
        ${r.last_error ? `<span class="world-meta" style="color:var(--color-warn)">${esc(r.last_error)}</span>` : ""}
      </div>
      <div class="github-repo-row__actions">
        <button type="button" class="button-outline-on-dark button-sm${syncing ? " is-busy" : ""}" data-github-sync="${r.id}" data-world-id="${esc(w.id)}"${syncing ? " disabled" : ""}>${syncing ? "Syncing…" : `Sync to ${esc(vaultStorageLabel())}`}</button>
        <button type="button" class="button-tertiary-text button-sm" data-github-unlink="${r.id}" data-world-id="${esc(w.id)}"${syncing ? " disabled" : ""}>Unlink</button>
      </div>
    </div>`;
  }).join("");

  if (!oauthOk) {
    return `<section class="github-repos-panel">
      <p class="section-eyebrow">GitHub</p>
      <p class="body-md muted">Add <code>GITHUB_CLIENT_ID</code> and <code>GITHUB_CLIENT_SECRET</code> to <code>.env</code>, register callback <code>${esc(status.redirect_uri || "/api/github/callback")}</code>, then restart.</p>
    </section>`;
  }

  if (!connected) {
    return `<section class="github-repos-panel">
      <p class="section-eyebrow">GitHub repositories</p>
      <p class="body-md muted">Authorize GitHub to browse your repos and sync docs into this world's knowledge graph (${esc(vaultStorageLabel())}).</p>
      <a class="button-primary button-sm" href="/api/github/auth/start?world_id=${encodeURIComponent(w.id)}">Connect GitHub</a>
    </section>`;
  }

  return `<section class="github-repos-panel">
    <div class="github-repos-panel__head">
      <div>
        <p class="section-eyebrow">GitHub repositories</p>
        <p class="body-md muted">Connected as <strong>${esc(status.user?.login || "GitHub")}</strong> — link multiple repos; files sync to ${esc(vaultStorageLabel())} with searchable descriptions.</p>
      </div>
    </div>
    <div class="human-form__row" style="align-items:flex-end">
      <label class="human-field" style="flex:1">
        <span class="caption-uppercase">Add repository</span>
        <select class="text-input-on-dark" id="github-repo-pick">
          <option value="">Select a repository…</option>
          ${pickOpts}
        </select>
      </label>
      <button type="button" class="button-primary button-sm" data-github-add="${esc(w.id)}"${state._syncingLinkIds.size ? " disabled" : ""}>Link &amp; sync</button>
    </div>
    <div class="github-repo-list">${linkedRows || "<p class='body-md muted'>No GitHub repos linked yet.</p>"}</div>
  </section>`;
}

function renderWorldVaultPanel(w) {
  if (!w || w.id === "root") return "";
  const vault = state._worldVault?.vault || state._worldVault || {};
  const facets = vault.facets || vault.folders || [];
  const counts = vault.domain_counts || {};
  const activeFacet = state.ui?.vaultFacet || facets[0]?.id || facets[0]?.folder || null;
  const showForm = state.ui?.vaultDocForm || state.ui?.vaultDocEdit;
  const facetDocs = (facets.find(f => (f.id || f.folder) === activeFacet) || {}).documents || [];

  const facetTabs = facets.map(f => {
    const id = f.id || f.folder;
    const n = (f.documents || []).length + (f.files || []).length;
    return `<button type="button" class="vault-facet-tab${id === activeFacet ? " is-active" : ""}" data-vault-facet="${esc(id)}">${esc(f.label)} <span class="badge-pill">${n}</span></button>`;
  }).join("");

  const docRows = facetDocs.map(d => `
    <article class="vault-doc-card" data-doc-id="${d.id}">
      <div class="vault-doc-card__head">
        <h4>${esc(d.title)}</h4>
        <span class="world-meta">${esc(d.filename || "")} · ${formatBytes(d.size_bytes)}${d.source_type === "github" ? " · GitHub" : ""}</span>
      </div>
      <p class="body-md">${esc(d.description || "No description")}</p>
      <div class="vault-doc-card__actions">
        <button type="button" class="button-outline-on-dark button-sm" data-vault-edit-doc="${d.id}">Edit</button>
        <button type="button" class="button-tertiary-text button-sm" data-vault-delete-doc="${d.id}">Remove</button>
      </div>
    </article>`).join("");

  const diskFiles = (facets.find(f => (f.id || f.folder) === activeFacet) || {}).files || [];
  const diskList = diskFiles.length ? `<ul class="vault-file-list">${diskFiles.map(file =>
    `<li class="mono">${esc(file.relative || file.name)} <span class="muted">on disk</span></li>`
  ).join("")}</ul>` : "";

  return `
    <section class="driver-card vault-panel knowledge-panel" style="margin-top:var(--space-md)">
      <div class="vault-panel-head">
        <div>
          <p class="section-eyebrow">Knowledge graph</p>
          <h3 class="title-sm">${esc(w.name)} — ${esc(vault.template_id || w.template || "startup")} template</h3>
          <p class="body-md muted">Category slots for this world type. Add docs with a searchable description; large files live in ${esc(vaultStorageLabel())}. Use the <strong>Files</strong> tab in the map above for the full folder graph.</p>
          <p class="world-meta">${vault.document_count || 0} registered docs · ${esc(vault.vault_path || "")}${vault.repo_path ? ` · repo: ${esc(vault.repo_path)}` : ""}</p>
        </div>
        <div class="vault-panel-actions">
          <button type="button" class="button-primary button-sm" data-vault-add-doc="${esc(w.id)}">Add document</button>
          <button type="button" class="button-outline-on-dark button-sm" data-world-graph-tab="vault">Open file map</button>
          <input class="text-input-on-dark" id="vault-repo-path" placeholder="Local repo path" value="${esc(w.repo_path || "")}">
          <button type="button" class="button-outline-on-dark button-sm" data-vault-link="${esc(w.id)}">Link repo</button>
          <button type="button" class="button-outline-on-dark button-sm" data-vault-ingest="${esc(w.id)}">Re-ingest</button>
        </div>
      </div>
      ${renderGithubReposPanel(w, vault)}
      <div class="vault-inline-graph graph-wrap">
        <p class="caption-uppercase">File &amp; folder map</p>
        <div id="graph-vault-inline" class="graph-canvas graph-canvas--vault" role="img" aria-label="Vault file map"></div>
      </div>
      <div class="vault-facet-tabs" role="tablist">${facetTabs || "<span class='muted'>No categories</span>"}</div>
      ${showForm ? renderVaultDocForm(w, facets, activeFacet) : ""}
      <div class="vault-doc-grid">${docRows || "<p class='body-md muted'>No documents in this slot yet — add your ICP, GTM notes, research, etc.</p>"}</div>
      ${diskList}
      <div class="vault-search-row">
        <input class="text-input-on-dark" id="vault-search-q" placeholder="Search descriptions in this world…">
        <button type="button" class="button-outline-on-dark button-sm" data-vault-search="${esc(w.id)}">Search</button>
      </div>
      <pre class="vault-search-results mono" id="vault-search-results" hidden></pre>
      <details class="vault-legacy-facets" style="margin-top:var(--space-md)">
        <summary class="caption-uppercase">All slots overview</summary>
        <div class="vault-facet-grid" style="margin-top:var(--space-sm)">${facets.map(f => `
          <article class="vault-facet-card">
            <div class="vault-facet-head"><h4>${esc(f.label)}</h4><span class="badge-pill">${f.file_count || 0}</span></div>
            <p class="world-meta">${esc(f.folder)}/ · ${counts[f.domain] || 0} vectors</p>
          </article>`).join("")}</div>
      </details>
    </section>`;
}

function formatBytes(n) {
  const b = Number(n) || 0;
  if (b < 1024) return `${b} B`;
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1048576).toFixed(1)} MB`;
}

function renderWorld() {
  const w = state._worldFull || {};
  const tree = w.worlds || state.worlds || {};
  const root = tree.root || {};
  const children = tree.children || [];
  const inspectId = inspectorWorldId();
  const activeId = currentWorldId();
  const selected = worldById(inspectId) || root;
  const snap = w.snapshot || state.snapshot || {};
  const founder = state.config?.my_name || "You";
  if (isRootWorld(selected) && worldGraphTab === "vault") worldGraphTab = "hierarchy";
  const showVaultGraphTab = !isRootWorld(selected);

  return `
    <div class="worlds-page">
      <section class="worlds-hero">
        <div class="worlds-hero-lead">
          <h2>${esc(founder)}'s world map</h2>
          <p><strong>Your venture map</strong> — create worlds, set context, link doc repos, and switch active context. You define each world; agents read what you write.</p>
        </div>
        <div class="worlds-stat">
          <span class="n">${children.length + 1}</span>
          <span class="l">Worlds</span>
        </div>
        <div class="worlds-stat">
          <span class="n">${children.length}</span>
          <span class="l">Sub-worlds</span>
        </div>
        <div class="worlds-stat">
          <span class="n" style="font-size:1rem;padding-top:6px">${esc(activeWorldLabel())}</span>
          <span class="l">Active context</span>
        </div>
      </section>

      <div class="worlds-workspace">
        <section class="worlds-panel">
          <div class="worlds-panel-head">
            <h3>Hierarchy</h3>
          </div>
          <div class="worlds-panel-body">
            ${renderWorldTreeNav(root, children, inspectId, activeId)}
          </div>
        </section>

        <section class="worlds-panel">
          <div class="worlds-panel-head">
            <h3>Map</h3>
            <div class="world-graph-tabs" role="tablist">
              <button type="button" class="world-graph-tab${worldGraphTab === "hierarchy" ? " is-active" : ""}" data-world-graph-tab="hierarchy">Hierarchy</button>
              <button type="button" class="world-graph-tab${worldGraphTab === "ecosystem" ? " is-active" : ""}" data-world-graph-tab="ecosystem">Ecosystem</button>
              ${showVaultGraphTab ? `<button type="button" class="world-graph-tab${worldGraphTab === "vault" ? " is-active" : ""}" data-world-graph-tab="vault">Files</button>` : ""}
            </div>
          </div>
          <div id="graph-world" class="graph-canvas world-graph-canvas" role="img" aria-label="World graph"></div>
          <div class="world-graph-legend">
            ${worldGraphTab === "vault" ? `
            <span><i style="border-color:#051f13"></i> World</span>
            <span><i style="border-color:#00666b"></i> Folder</span>
            <span><i style="border-color:#8f706b;border-radius:50%"></i> File</span>
            <span><i style="border-color:#f75440;background:#2d312e"></i> GitHub</span>
            ` : `
            <span><i style="border-color:#051f13"></i> Main</span>
            <span><i style="border-color:#f75440"></i> Project</span>
            <span><i style="border-color:#ffb4a8"></i> Idea</span>
            <span><i style="border-color:#00666b"></i> Research</span>
            <span><i style="border-color:#f75440;background:#f7544033"></i> Active</span>
            `}
          </div>
        </section>

        <section class="worlds-panel">
          <div class="worlds-panel-head">
            <h3>Inspector</h3>
          </div>
          <div class="worlds-panel-body" id="world-inspector">
            ${renderWorldInspector(selected, snap)}
          </div>
        </section>
      </div>

      ${!isRootWorld(selected) ? renderWorldVaultPanel(selected) : ""}

      <section class="world-create-panel driver-card${state.ui?.worldCreateOpen ? " is-open" : ""}" id="world-create-panel">
        <div class="world-create-panel__head">
          <div>
            <p class="section-eyebrow">You create</p>
            <h3 class="title-sm">New world</h3>
            <p class="body-md muted">Add a venture, project, or idea under your root world. You choose the context — agents only use what you define.</p>
          </div>
          <button type="button" class="button-outline-on-dark button-sm" data-toggle-ui="worldCreateOpen" aria-expanded="${state.ui?.worldCreateOpen ? "true" : "false"}">
            ${state.ui?.worldCreateOpen ? "Hide form" : "Create world"}
          </button>
        </div>
        ${state.ui?.worldCreateOpen ? renderWorldCreateForm("world-create-form") : ""}
      </section>
    </div>`;
}

function isRootWorld(w) {
  return !w || w.id === "root";
}

function renderChat() {
  const agents = state._agents || {};
  const meta = routingMeta(agents);
  const routeLabel = routingLabel(agents);
  const direct = isDirectSpecialist();
  const specs = listSpecialists(agents);
  const ragMode = state.ragMode || "auto";
  const ragMeta = RAG_MODES.find(m => m.id === ragMode) || RAG_MODES[0];
  const msgs = chatHistory.map(m =>
    `<div class="msg ${m.role}"><div class="msg-bubble">${esc(m.text)}</div></div>`
  ).join("");
  const live = state.live || {};
  const empty = !chatHistory.length;
  const recentRuns = collectAgentRuns().slice(0, 4);
  return `<div class="chat-shell">
    <header class="chat-header driver-card">
      <div>
        <p class="section-eyebrow">Optional · agent assist</p>
        <h2 class="title-md">Ask agent</h2>
      </div>
      <div class="chat-header__meta">
        <span class="badge-pill">${esc(activeWorldLabel())}</span>
        <span class="badge-pill agent-routing-badge">${esc(routeLabel)}</span>
        <button type="button" class="button-outline-on-dark button-sm" data-goto="agents">Change specialist</button>
      </div>
    </header>
    <div class="chat-layout chat-layout--rich">
      <div class="chat-wrap">
        <div class="chat-messages${empty ? " is-empty" : ""}" id="chat-messages">
          ${empty ? `<div class="chat-empty">
            <p class="title-md">Supervisor ready</p>
            <p class="body-md">Routing: <strong>${esc(routeLabel)}</strong> · Retrieval: <strong>${esc(ragMeta.label)}</strong></p>
            <div class="chat-empty__chips">${specs.map(s =>
              `<button type="button" class="delegate-hint" data-goto="agents">${esc(s.label)}</button>`
            ).join("")}</div>
          </div>` : msgs}
        </div>
        <div class="chat-composer driver-card">
          <div class="chat-composer__controls">
            ${renderRagModeSelect("rag-mode-select")}
          </div>
          <div class="chat-input-row">
            <textarea class="text-input-on-dark chat-input" id="chat-input" placeholder="${direct ? `Task for ${esc(meta.label)}…` : "Message supervisor…"}" rows="3"></textarea>
            <button class="button-primary" id="chat-send">${direct ? `Run ${esc(meta.label)}` : "Send"}</button>
          </div>
          <div class="chat-toolbar">
            <label class="button-outline-on-dark button-sm upload-label">Upload<input type="file" id="chat-file" hidden accept=".pdf,.docx,.txt,.md,.csv,.json"></label>
            <button type="button" class="button-outline-on-dark button-sm" id="chat-clear">Clear</button>
            <button type="button" class="button-outline-on-dark button-sm" data-goto="world">Worlds</button>
          </div>
        </div>
      </div>
      <aside class="chat-rail">
        ${renderLivePanel(live, "chat-live-panel")}
        <section class="driver-card chat-rail-card">
          <p class="caption-uppercase">Specialists</p>
          <div class="specialist-chips" style="margin-top:var(--space-xxs)">${specs.map(s =>
            `<span class="specialist-chip${currentSpecialistId() === s.id ? " is-selected" : ""}${agentBusy(live, s.id) ? " is-busy" : ""}">${esc(s.label)}</span>`
          ).join("")}</div>
        </section>
        <section class="driver-card chat-rail-card">
          <p class="caption-uppercase">Runtime</p>
          <div id="graph-runtime-chat" class="graph-canvas graph-canvas--compact" style="margin-top:var(--space-xxs)"></div>
        </section>
        ${recentRuns.length ? `<section class="driver-card chat-rail-card">
          <p class="caption-uppercase">Recent runs</p>
          <div class="activity-timeline">${recentRuns.map(r =>
            `<div class="activity-timeline__row"><span>${esc((r.agent || "").toUpperCase())}</span><span class="muted">${esc((r.task || "").slice(0, 40))}</span></div>`
          ).join("")}</div>
        </section>` : ""}
      </aside>
    </div>
  </div>`;
}

function renderApprovals() {
  const appr = state.approvals || [];
  if (!appr.length) {
    return `<section class="driver-card empty-state"><p class="title-sm">No pending approvals</p></section>`;
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
  const formOpen = !!state.ui?.crmFormOpen;
  const pipeRows = Object.entries(pipeline).map(([k, v]) =>
    `<div class="kv"><span class="k">${esc(k)}</span><span class="v">${v}</span></div>`
  ).join("") || "<p class='muted'>No pipeline data</p>";

  const statusOpts = (cur) => CRM_STATUSES.map(s =>
    `<option value="${s}"${s === cur ? " selected" : ""}>${esc(s)}</option>`
  ).join("");

  const rows = contacts.slice(0, 50).map(c => `<tr>
    <td>${esc(c.name)}</td><td>${esc(c.company || "—")}</td><td>${esc(c.role || "—")}</td>
    <td><select class="text-input-on-dark crm-status-select" data-crm-status="${c.id}" aria-label="Status for ${esc(c.name)}">${statusOpts(c.status || "prospect")}</select></td>
    <td class="muted">${esc(c.email || "")}</td></tr>`).join("");

  const fu = followups.map(c => `<li>${esc(c.name)} @ ${esc(c.company || "?")}</li>`).join("") || "<li class='muted'>None due</li>";

  return `<div class="dashboard-grid">
    <section class="driver-card span-12 human-panel">
      <div class="human-panel__head">
        <div>
          <p class="section-eyebrow">CRM</p>
          <h3 class="title-sm">Contacts &amp; pipeline</h3>
          <p class="body-md muted">Add and update leads yourself. Status changes save immediately.</p>
        </div>
        <button type="button" class="button-primary button-sm" data-toggle-ui="crmFormOpen">${formOpen ? "Hide form" : "Add contact"}</button>
      </div>
      ${formOpen ? `
      <form class="human-form" id="crm-create-form">
        <div class="human-form__row">
          <label class="human-field"><span class="caption-uppercase">Name</span>
            <input class="text-input-on-dark" name="name" required placeholder="Full name"></label>
          <label class="human-field"><span class="caption-uppercase">Company</span>
            <input class="text-input-on-dark" name="company" placeholder="Company"></label>
        </div>
        <div class="human-form__row">
          <label class="human-field"><span class="caption-uppercase">Role</span>
            <input class="text-input-on-dark" name="role" placeholder="Title"></label>
          <label class="human-field"><span class="caption-uppercase">Email</span>
            <input class="text-input-on-dark" name="email" type="email" placeholder="email@company.com"></label>
        </div>
        <div class="human-form__row">
          <label class="human-field"><span class="caption-uppercase">Status</span>
            <select class="text-input-on-dark" name="status">${statusOpts("prospect")}</select></label>
          <label class="human-field"><span class="caption-uppercase">LinkedIn</span>
            <input class="text-input-on-dark" name="linkedin_url" placeholder="https://linkedin.com/in/…"></label>
        </div>
        <label class="human-field"><span class="caption-uppercase">Notes</span>
          <textarea class="text-input-on-dark" name="notes" rows="2" placeholder="Context for follow-ups"></textarea></label>
        <div class="human-form__actions">
          <button type="submit" class="button-primary button-sm">Save contact</button>
          <button type="button" class="button-outline-on-dark button-sm" data-toggle-ui="crmFormOpen">Cancel</button>
        </div>
      </form>` : ""}
    </section>
    <section class="driver-card span-4"><p class="caption-uppercase">Pipeline</p><div style="margin-top:var(--space-sm)">${pipeRows}</div></section>
    <section class="driver-card span-8"><p class="caption-uppercase">Follow-ups due</p><ul class="list-plain" style="margin-top:var(--space-sm)">${fu}</ul></section>
    <section class="band-light span-12">
      <p class="caption-uppercase" style="color:var(--color-muted)">Contacts (${contacts.length})</p>
      <div class="table-wrap"><table><thead><tr><th>Name</th><th>Company</th><th>Role</th><th>Status</th><th>Email</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="5" class="muted">No contacts yet — use Add contact above.</td></tr>'}</tbody></table></div>
    </section>
  </div>`;
}

function renderGoals() {
  const g = state._goals || {};
  const goalsFormOpen = !!state.ui?.goalsFormOpen;
  const reminderFormOpen = !!state.ui?.reminderFormOpen;
  const goals = (g.active || []).map(x => `<li class="goal-row">
    <span><strong>${esc(x.title)}</strong>${x.detail ? " — " + esc(x.detail) : ""}</span>
    <button type="button" class="button-outline-on-dark button-sm" data-goal-done="${x.id}">Done</button>
  </li>`).join("") || "<li class='muted'>No active goals — add one below.</li>";
  const tasks = (state.tasks || []).map(t => `<li>${esc(t.title)} <span class="muted">P${t.priority || 3}</span></li>`).join("") || "<li class='muted'>No open tasks</li>";
  const rems = (g.reminders || []).map(r => `<li>${esc(r.text)} <span class="muted">${esc(r.due_at)}</span></li>`).join("") || "<li class='muted'>No reminders</li>";
  const plans = (g.plans || []).map(p => `<li>${esc(p.goal)}</li>`).join("") || "<li class='muted'>No open plans</li>";

  return `<div class="dashboard-grid">
    <section class="driver-card span-12 human-panel">
      <div class="human-panel__head">
        <div>
          <p class="section-eyebrow">Goals</p>
          <h3 class="title-sm">Outcomes you own</h3>
          <p class="body-md muted">Track goals and reminders directly — no agent required.</p>
        </div>
        <div class="human-panel__actions">
          <button type="button" class="button-primary button-sm" data-toggle-ui="goalsFormOpen">${goalsFormOpen ? "Hide goal form" : "New goal"}</button>
          <button type="button" class="button-outline-on-dark button-sm" data-toggle-ui="reminderFormOpen">${reminderFormOpen ? "Hide reminder" : "Reminder"}</button>
        </div>
      </div>
      ${goalsFormOpen ? `
      <form class="human-form" id="goal-create-form">
        <div class="human-form__row">
          <label class="human-field"><span class="caption-uppercase">Goal</span>
            <input class="text-input-on-dark" name="title" required placeholder="What are you driving toward?"></label>
          <label class="human-field"><span class="caption-uppercase">Priority</span>
            <select class="text-input-on-dark" name="priority">
              <option value="1">P1 — critical</option>
              <option value="2">P2 — high</option>
              <option value="3" selected>P3 — normal</option>
              <option value="4">P4 — low</option>
              <option value="5">P5 — someday</option>
            </select></label>
        </div>
        <label class="human-field"><span class="caption-uppercase">Detail</span>
          <textarea class="text-input-on-dark" name="detail" rows="2" placeholder="Optional context"></textarea></label>
        <div class="human-form__actions">
          <button type="submit" class="button-primary button-sm">Add goal</button>
          <button type="button" class="button-outline-on-dark button-sm" data-toggle-ui="goalsFormOpen">Cancel</button>
        </div>
      </form>` : ""}
      ${reminderFormOpen ? `
      <form class="human-form" id="reminder-create-form" style="margin-top:var(--space-sm)">
        <div class="human-form__row">
          <label class="human-field"><span class="caption-uppercase">Reminder</span>
            <input class="text-input-on-dark" name="text" required placeholder="Follow up with…"></label>
          <label class="human-field"><span class="caption-uppercase">Due</span>
            <input class="text-input-on-dark" name="due_at" type="datetime-local" required></label>
        </div>
        <div class="human-form__actions">
          <button type="submit" class="button-primary button-sm">Save reminder</button>
          <button type="button" class="button-outline-on-dark button-sm" data-toggle-ui="reminderFormOpen">Cancel</button>
        </div>
      </form>` : ""}
    </section>
    <section class="driver-card span-6"><p class="caption-uppercase">Active goals</p><ul class="list-plain goal-list" style="margin-top:var(--space-sm)">${goals}</ul></section>
    <section class="driver-card span-6"><p class="caption-uppercase">Open tasks</p><ul class="list-plain" style="margin-top:var(--space-sm)">${tasks}</ul></section>
    <section class="driver-card span-6"><p class="caption-uppercase">Reminders</p><ul class="list-plain" style="margin-top:var(--space-sm)">${rems}</ul></section>
    <section class="driver-card span-6"><p class="caption-uppercase">Plans &amp; projects</p><ul class="list-plain" style="margin-top:var(--space-sm)">${plans}</ul></section>
  </div>`;
}

function renderMemory() {
  const results = state._memoryResults || [];
  const m = state._memoryFull || {};
  const cols = m.collections || [];
  const kg = m.knowledge_graph || {};
  const items = results.map(r => `<div class="memory-hit">
    <span class="badge-pill">${esc(r.collection)}</span>
    <p class="body-md" style="margin-top:var(--space-xxs);max-width:72ch">${esc(r.text)}</p></div>`).join("");
  const colCards = cols.map(c => `
    <div class="memory-collection">
      <h4>${esc(c.name)} <span class="muted">(${c.count} vectors)</span></h4>
      ${(c.samples || []).map(s => `<p class="memory-sample">${esc(s.text)}</p>`).join("") || "<p class='muted'>Empty collection</p>"}
    </div>`).join("");
  return `
    <div class="search-row">
      <input type="search" class="text-input-on-dark" id="memory-q" placeholder="Semantic search across all memory…" value="${esc(state._memoryQ || "")}">
      <button class="button-primary" id="memory-search">Search</button>
    </div>
    <div class="graph-tabs">
      <button type="button" class="graph-tab ${memoryGraphTab === "graph" ? "is-active" : ""}" data-memory-tab="graph">Memory graph</button>
      <button type="button" class="graph-tab ${memoryGraphTab === "collections" ? "is-active" : ""}" data-memory-tab="collections">Collections</button>
      <button type="button" class="graph-tab ${memoryGraphTab === "search" ? "is-active" : ""}" data-memory-tab="search">Search results</button>
    </div>
    <div id="memory-tab-graph" ${memoryGraphTab !== "graph" ? "hidden" : ""}>
      <p class="body-md" style="margin-bottom:var(--space-sm)">Knowledge graph (${(kg.entities || []).length} entities, ${(kg.relations || []).length} relations) plus recent vector memory chunks.</p>
      <div id="graph-memory" class="graph-canvas"></div>
      <div class="graph-detail" id="graph-memory-detail">Click a node to inspect</div>
    </div>
    <div id="memory-tab-collections" ${memoryGraphTab !== "collections" ? "hidden" : ""}>${colCards || "<p class='body-md'>No vector memory yet.</p>"}</div>
    <div id="memory-tab-search" ${memoryGraphTab !== "search" ? "hidden" : ""}>
      <div id="memory-results">${items || '<p class="body-md">Search to find relevant memories.</p>'}</div>
    </div>`;
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
  const full = state._activity?.traces_full || [];
  const actions = state._activity?.actions || state.actions || [];
  const tracesHtml = full.length ? full.map(t => `
    <article class="trace-card">
      <div class="trace-card-head">
        <span class="mono">${esc(t.actor)}</span>
        <span class="muted">${t.duration_s}s</span>
      </div>
      <p class="message">${esc(t.message)}</p>
      ${renderLiveFlow(t.events, "No tools in this turn")}
      ${t.final ? `<p class="world-meta" style="margin-top:var(--space-xs)">→ ${esc(t.final)}</p>` : ""}
    </article>`).join("") : "<p class='body-md muted'>No agent turns logged today. Send a message in Chat to see the decision flow here.</p>";
  const act = actions.slice(0, 20).map(a => `<div class="activity-row">
    <div class="mono">${esc(a.tool_name)}</div>
    <div class="meta">${esc(a.actor)} · ${esc((a.created_at || "").slice(0, 16))}</div></div>`).join("") || "<p class='muted'>No actions logged.</p>";
  return `<div class="dashboard-grid">
    <section class="driver-card span-8"><p class="caption-uppercase">Decision flow</p><div style="margin-top:var(--space-sm)">${tracesHtml}</div></section>
    <section class="driver-card span-4"><p class="caption-uppercase">Tool log</p><div style="margin-top:var(--space-sm)">${act}</div></section>
  </div>`;
}

function infraKvRow(label, value, mono = false) {
  const val = value == null || value === "" ? "—" : String(value);
  return `<div class="infra-kv"><dt>${esc(label)}</dt><dd${mono ? ' class="infra-kv__val"' : ""}>${esc(val)}</dd></div>`;
}

function infraHealthCard(title, ok, rows, detail) {
  const status = ok ? "Healthy" : "Issue";
  return `<div class="integration-card infra-health-card${ok ? " is-connected" : " is-warning"}">
    <div class="integration-card__head">
      <span class="title-sm">${esc(title)}</span>
      <span class="integration-card__status">${status}</span>
    </div>
    <dl class="infra-kv-list">${rows}</dl>
    ${detail ? `<p class="integration-card__detail">${esc(detail)}</p>` : ""}
  </div>`;
}

function renderInfrastructureHealth() {
  const h = state._infraHealth;
  if (!h) {
    return `<section class="driver-card span-12">
      <div class="infra-health-head">
        <p class="caption-uppercase">Infrastructure</p>
        <button type="button" class="button-outline-on-dark button-sm" id="btn-infra-refresh">Check health</button>
      </div>
      <p class="body-md muted" style="margin-top:var(--space-sm)">Monitor EC2 host, S3 vault bucket, and disk on this server.</p>
    </section>`;
  }
  const host = h.host || {};
  const s3 = h.s3 || {};
  const disk = h.disk || {};
  const app = h.app || {};
  const hostRows = host.platform === "ec2"
    ? infraKvRow("Instance", host.instance_id, true)
      + infraKvRow("Region", host.region)
      + infraKvRow("Type", host.instance_type)
      + infraKvRow("IAM role", host.iam_role)
    : infraKvRow("Host", "Local / dev");
  const s3Rows = s3.configured
    ? infraKvRow("Bucket", s3.bucket, true)
      + infraKvRow("Region", s3.region)
      + infraKvRow("Read/write", s3.read_write_ok ? "OK" : (s3.reachable ? "Reachable only" : "Failed"))
    : infraKvRow("Storage", "Local disk only");
  const diskRows = infraKvRow("Data path", disk.path, true)
    + infraKvRow("Free", disk.free_gb != null ? `${disk.free_gb} GB` : null)
    + infraKvRow("Used", disk.used_pct != null ? `${disk.used_pct}%` : null);
  const overallOk = !!h.ok;
  return `<section class="driver-card span-12">
    <div class="infra-health-head">
      <div>
        <p class="caption-uppercase">Infrastructure</p>
        <p class="world-meta">Last checked ${esc(fmtTime(h.checked_at) || h.checked_at || "—")} · App storage: <strong>${esc(app.storage_backend || "—")}</strong></p>
      </div>
      <div class="infra-health-head__actions">
        <span class="badge-pill${overallOk ? " badge-pill--ok" : " badge-pill--warn"}">${overallOk ? "All checks passed" : "Needs attention"}</span>
        <button type="button" class="button-outline-on-dark button-sm" id="btn-infra-refresh">Refresh</button>
      </div>
    </div>
    <div class="infra-health-grid">
      ${infraHealthCard("EC2 host", host.ok !== false, hostRows, host.detail)}
      ${infraHealthCard("S3 vault", s3.configured ? !!s3.ok : true, s3Rows, s3.detail)}
      ${infraHealthCard("Disk", !!disk.ok, diskRows, disk.detail)}
    </div>
  </section>`;
}

function integrationCard(name, connected, detail) {
  return `<div class="integration-card${connected ? " is-connected" : ""}">
    <div class="integration-card__head">
      <span class="title-sm">${esc(name)}</span>
      <span class="integration-card__status">${connected ? "Active" : "Not configured"}</span>
    </div>
    <p class="integration-card__detail">${esc(detail)}</p>
  </div>`;
}

function renderSettings() {
  const c = state.config || {};
  const integ = c.integrations || {};
  const level = (c.autonomy_level || "balanced").toLowerCase();
  const pauseBtn = c.agent_paused
    ? `<button type="button" class="button-primary" id="toggle-pause">Resume agent</button>`
    : `<button type="button" class="button-outline-on-dark" id="toggle-pause">Pause agent</button>`;
  return `<div class="dashboard-grid settings-page">
    ${renderInfrastructureHealth()}
    <section class="driver-card span-4 settings-panel">
      <p class="caption-uppercase">Identity</p>
      <dl class="settings-kv" style="margin-top:var(--space-sm)">
        <div class="settings-kv__row"><dt>Name</dt><dd>${esc(c.my_name)}</dd></div>
        <div class="settings-kv__row"><dt>Company</dt><dd>${esc(c.company_name)}</dd></div>
      </dl>
      <p class="body-md muted" style="margin-top:var(--space-sm)">Edit identity in <code>.env</code> — restart to persist.</p>
    </section>
    <section class="driver-card span-8 human-panel">
      <p class="section-eyebrow">Your policy</p>
      <h3 class="title-sm">Agent behavior</h3>
      <p class="body-md muted" style="margin-bottom:var(--space-sm)">You set how much the agent can do without asking. Changes apply for this session.</p>
      <form class="human-form" id="agent-config-form">
        <div class="human-form__row">
          <label class="human-field"><span class="caption-uppercase">Autonomy</span>
            <select class="text-input-on-dark" name="autonomy_level">
              <option value="cautious"${level === "cautious" ? " selected" : ""}>Cautious — ask before most actions</option>
              <option value="balanced"${level === "balanced" ? " selected" : ""}>Balanced — routine tools auto-run</option>
              <option value="autonomous"${level === "autonomous" ? " selected" : ""}>Autonomous — minimal prompts</option>
            </select></label>
          <label class="human-field human-field--checkbox">
            <input type="checkbox" name="auto_approve" value="1"${c.auto_approve ? " checked" : ""}>
            <span>Auto-approve low-risk tool calls</span>
          </label>
        </div>
        <div class="human-form__actions">
          <button type="submit" class="button-primary button-sm">Save policy</button>
          ${pauseBtn}
        </div>
      </form>
    </section>
    <section class="driver-card span-4 settings-panel">
      <p class="caption-uppercase">Channels</p>
      <dl class="settings-kv" style="margin-top:var(--space-sm)">
        <div class="settings-kv__row"><dt>Web UI</dt><dd>${c.web_ui_enabled ? "On" : "Off"}</dd></div>
        <div class="settings-kv__row"><dt>Telegram</dt><dd>${c.telegram_enabled ? "On" : "Off"}</dd></div>
        <div class="settings-kv__row"><dt>Port</dt><dd>${c.dashboard_port}</dd></div>
      </dl>
    </section>
    <section class="driver-card span-4">
      <p class="caption-uppercase">Access</p>
      <p class="body-md muted" style="margin-top:var(--space-sm)">Lock this dashboard on shared or production hosts with a 6-digit PIN (<code>DASHBOARD_PIN</code> in <code>.env</code>).</p>
      <div class="human-form__actions" style="margin-top:var(--space-sm)">
        <button type="button" class="button-outline-on-dark button-sm" id="btn-logout">Lock dashboard</button>
      </div>
    </section>
    <section class="driver-card span-8">
      <p class="caption-uppercase">Integrations</p>
      <div class="integration-grid" style="margin-top:var(--space-sm)">
        ${integrationCard("Gmail", integ.gmail, "SMTP send + IMAP inbox via app password")}
        ${integrationCard("Google Calendar", integ.calendar, "OAuth token in data/google_token.json")}
        ${integrationCard("Qdrant", integ.qdrant, "Vector memory + knowledge vault")}
        ${integrationCard("X / Twitter", integ.x, "Posting and monitoring API keys")}
        ${integrationCard("Serper", integ.serper, "Web search")}
        ${integrationCard("Tavily", integ.tavily, "Research search")}
        ${integrationCard("GitHub", integ.github || integ.github_oauth, integ.github ? "Connected — link repos in Worlds" : (integ.github_oauth ? "OAuth ready — connect in Worlds" : "Set GITHUB_CLIENT_ID in .env"))}
      </div>
    </section>
  </div>`;
}

// ── Navigation ───────────────────────────────────────────────────────────────

async function loadViewData(view) {
  if (view === "crm") state._crm = await api("/crm/contacts");
  if (view === "goals") state._goals = await api("/goals");
  if (view === "tools") state._tools = await api("/tools");
  if (view === "agents") {
    const [ag, act, runs, crm, tools] = await Promise.all([
      api("/agents"),
      api("/activity").catch(() => ({})),
      api("/agents/runs").catch(() => ({ runs: [], actions: [] })),
      api("/crm/contacts").catch(() => ({})),
      api("/tools").catch(() => ({})),
    ]);
    state._agents = ag;
    if (!state._agents?.specialists?.length) {
      state._agents = { ...state._agents, specialists: DEFAULT_SPECIALISTS };
    }
    state._activity = act;
    state._agentRunsApi = runs.runs || [];
    state._agentActions = runs.actions || act.actions || [];
    state._crm = crm;
    state._tools = tools;
    const wid = currentWorldId();
    if (wid && wid !== "root") {
      const res = await api(`/worlds/${encodeURIComponent(wid)}/vault`).catch(() => ({}));
      state._worldVault = res.vault || null;
      state._vaultGraph = res.vault_graph || null;
    } else {
      state._worldVault = null;
      state._vaultGraph = null;
    }
  }
  if (view === "settings") {
    state._infraHealth = await api("/infrastructure/health").catch(() => state._infraHealth || null);
  }
  if (view === "activity") state._activity = await api("/activity");
  if (view === "world") {
    state._worldFull = await api("/graph/world");
    state._worldPreviews = state._worldFull?.world_previews || {};
    if (!state._worldTemplates?.length) {
      state._worldTemplates = (await api("/world-templates").catch(() => ({}))).templates || [];
    }
    if (!state.inspectorWorldId) state.inspectorWorldId = currentWorldId();
    state._githubStatus = await api("/github/status").catch(() => ({}));
    if (state._githubStatus?.connected) {
      state._githubRepos = (await api("/github/repos").catch(() => ({}))).repos || [];
    } else {
      state._githubRepos = [];
    }
    await loadWorldVault(inspectorWorldId());
    await resumeActiveSyncJobs(inspectorWorldId());
  }
  if (view === "memory") state._memoryFull = await api("/graph/memory");
  if (view === "dashboard" || view === "chat" || view === "agents") {
    if (!state._agents?.specialists?.length) {
      state._agents = await api("/agents").catch(() => ({ specialists: DEFAULT_SPECIALISTS }));
    }
  }
  if (view === "chat") {
    state._activity = await api("/activity").catch(() => state._activity || {});
    state._agentRunsApi = (await api("/agents/runs").catch(() => ({}))).runs || state._agentRunsApi;
  }
  if (view === "dashboard") {
    state._world = await api("/world").catch(() => state._world || {});
  }
  await loadGraphData();
}

function mobilePrimaryViews() {
  return window.FOS_MOBILE_PRIMARY_VIEWS || new Set(["dashboard", "chat", "agents", "world"]);
}

function closeMobileShell() {
  document.getElementById("sidebar")?.classList.remove("is-open");
  document.body.classList.remove("mobile-nav-open");
  const backdrop = document.getElementById("sidebar-backdrop");
  if (backdrop) {
    backdrop.classList.remove("is-visible");
    backdrop.setAttribute("hidden", "");
  }
  document.getElementById("mobile-menu-drawer")?.close?.();
}

function openSidebar() {
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  if (!sidebar || !backdrop) return;
  sidebar.classList.add("is-open");
  document.body.classList.add("mobile-nav-open");
  backdrop.removeAttribute("hidden");
  requestAnimationFrame(() => backdrop.classList.add("is-visible"));
}

function syncMobileNav(view) {
  const primary = mobilePrimaryViews();
  document.querySelectorAll(".mobile-tab").forEach(tab => {
    const v = tab.dataset.mobileView;
    if (v === "more") tab.classList.toggle("is-active", !primary.has(view));
    else tab.classList.toggle("is-active", v === view);
  });
  document.querySelectorAll(".mobile-menu-link").forEach(btn => {
    btn.classList.toggle("is-active", btn.dataset.view === view);
  });
}

function goView(view) {
  currentView = view;
  $$(".nav button").forEach(b => b.classList.toggle("is-active", b.dataset.view === view));
  $("#view-title").textContent = TITLES[view] || view;
  syncMobileNav(view);
  closeMobileShell();
  FOSMotion?.animateTopbarTitle?.();
  if (["dashboard", "agents", "chat", "activity", "world"].includes(view)) startLivePoll();
  else stopLivePoll();
  render();
  loadViewData(view).then(() => {
    render();
    afterRender();
    if (state._scrollWorldCreate && view === "world") {
      state._scrollWorldCreate = false;
      requestAnimationFrame(() => document.getElementById("world-create-panel")?.scrollIntoView({ behavior: "smooth", block: "nearest" }));
    }
  }).catch(console.error);
}

function afterRender() {
  try {
    if (currentView === "dashboard") drawDashboardCharts();
  } catch (e) {
    console.warn("dashboard charts skipped:", e);
  }
  try {
    drawGraphs();
  } catch (e) {
    console.warn("graphs skipped:", e);
  }
  pollLive();
  if (state._motionSkipOnce) {
    state._motionSkipOnce = false;
  } else {
    FOSMotion?.runView?.(currentView);
  }
  FOSMotion?.ensureContentVisible?.();
}

function animateLatestChatMessage() {
  requestAnimationFrame(() => {
    const msgs = $("#chat-messages")?.querySelectorAll(".msg:not(.system)");
    const last = msgs?.[msgs.length - 1];
    FOSMotion?.animateNewMessage?.(last);
  });
}

function render() {
  const el = $("#content");
  if (!el) return;
  const fns = {
    dashboard: renderDashboard, chat: renderChat, agents: renderAgents,
    world: renderWorld, approvals: renderApprovals, crm: renderCrm, goals: renderGoals,
    memory: renderMemory, tools: renderTools, activity: renderActivity,
    settings: renderSettings,
  };
  try {
    el.innerHTML = (fns[currentView] || renderDashboard)();
  } catch (e) {
    console.error("render failed:", e);
    el.innerHTML = `<div class="driver-card span-12">
      <p class="title-md">Dashboard could not render</p>
      <p class="body-md muted" style="margin-top:8px">${esc(e?.message || String(e))}</p>
      <button type="button" class="button-primary button-sm" id="render-retry" style="margin-top:12px">Retry</button>
    </div>`;
    $("#render-retry")?.addEventListener("click", () => boot());
    return;
  }
  document.querySelector(".content")?.classList.toggle("content--worlds", currentView === "world");
  document.querySelector(".content")?.classList.toggle("content--wide", ["agents", "world", "activity", "chat"].includes(currentView));
  document.querySelector(".content")?.classList.toggle("content--chat", currentView === "chat");
  populateSpecialistSelect();
  const ragEl = $("#rag-mode-select");
  if (ragEl) ragEl.value = state.ragMode || "auto";
  afterRender();
  if (currentView === "chat") {
    const chatEl = $("#chat-messages");
    if (chatEl) chatEl.scrollTop = chatEl.scrollHeight;
  }
}

/** Event delegation on #content — bound once so re-renders do not stack listeners. */
function initContentDelegation() {
  const root = document.getElementById("content");
  if (!root || root.dataset.delegation === "1") return;
  root.dataset.delegation = "1";

  root.addEventListener("click", e => {
    const el = e.target.closest(
      "[data-operator],[data-toggle-ui],[data-goto],[data-approve],[data-reject],"
      + "[data-select-specialist],[data-agents-tab],[data-toggle-run],[data-memory-tab],"
      + "[data-inspect-world],[data-world-graph-tab],[data-use-world],[data-set-active-world],"
      + "[data-edit-world],[data-cancel-edit],[data-delete-world],[data-vault-ingest],"
      + "[data-vault-link],[data-vault-search],[data-vault-facet],[data-vault-add-doc],"
      + "[data-vault-cancel-doc],[data-vault-edit-doc],[data-vault-delete-doc],"
      + "[data-github-add],[data-github-sync],[data-github-unlink],[data-goal-done],"
      + "#chat-send,#chat-clear,#memory-search,#toggle-pause,#agents-vault-search,"
      + "#delegate-selected-btn,#btn-logout,#btn-infra-refresh"
    );
    if (!el) return;
    if (el.id === "chat-send") return sendChat();
    if (el.id === "chat-clear") {
      chatHistory = [];
      localStorage.setItem("fos_chat", "[]");
      return render();
    }
    if (el.id === "memory-search") return searchMemory();
    if (el.id === "toggle-pause") return togglePause();
    if (el.id === "agents-vault-search") return agentsVaultSearch();
    if (el.id === "delegate-selected-btn") return delegateAgent();
    if (el.id === "btn-logout") return logoutPin();
    if (el.id === "btn-infra-refresh") return refreshInfraHealth();
    if (el.dataset.operator) return openOperatorAction(el.dataset.operator);
    if (el.dataset.toggleUi) {
      if (!state.ui) state.ui = {};
      state.ui[el.dataset.toggleUi] = !state.ui[el.dataset.toggleUi];
      return render();
    }
    if (el.dataset.goto) return goView(el.dataset.goto);
    if (el.dataset.approve) return decideApproval(el.dataset.approve, true);
    if (el.dataset.reject) return decideApproval(el.dataset.reject, false);
    if (el.dataset.selectSpecialist !== undefined) return selectSpecialist(el.dataset.selectSpecialist || "");
    if (el.dataset.agentsTab) {
      state.agentsTab = el.dataset.agentsTab;
      localStorage.setItem("fos_agents_tab", state.agentsTab);
      render();
      return drawGraphs();
    }
    if (el.dataset.toggleRun) {
      const id = el.dataset.toggleRun;
      state.expandedRunId = state.expandedRunId === id ? null : id;
      return render();
    }
    if (el.dataset.memoryTab) { memoryGraphTab = el.dataset.memoryTab; return render(); }
    if (el.dataset.inspectWorld) return selectInspectorWorld(el.dataset.inspectWorld);
    if (el.dataset.worldGraphTab) { worldGraphTab = el.dataset.worldGraphTab; return render(); }
    if (el.dataset.useWorld) { setActiveWorld(el.dataset.useWorld); return goView("chat"); }
    if (el.dataset.setActiveWorld) { setActiveWorld(el.dataset.setActiveWorld); return render(); }
    if (el.dataset.editWorld) { state.worldEditing = el.dataset.editWorld; return render(); }
    if (el.dataset.cancelEdit !== undefined) { state.worldEditing = null; return render(); }
    if (el.dataset.deleteWorld) return deleteWorld(el.dataset.deleteWorld);
    if (el.dataset.vaultIngest) return vaultIngest(el.dataset.vaultIngest);
    if (el.dataset.vaultLink) return vaultLinkRepo(el.dataset.vaultLink);
    if (el.dataset.vaultSearch) return vaultSearch(el.dataset.vaultSearch);
    if (el.dataset.vaultFacet) {
      if (!state.ui) state.ui = {};
      state.ui.vaultFacet = el.dataset.vaultFacet;
      return render();
    }
    if (el.dataset.vaultAddDoc !== undefined) {
      if (!state.ui) state.ui = {};
      state.ui.vaultDocForm = true;
      state.ui.vaultDocEdit = null;
      return render();
    }
    if (el.dataset.vaultCancelDoc !== undefined) {
      if (state.ui) { state.ui.vaultDocForm = false; state.ui.vaultDocEdit = null; }
      return render();
    }
    if (el.dataset.vaultEditDoc) return startVaultDocEdit(inspectorWorldId(), el.dataset.vaultEditDoc);
    if (el.dataset.vaultDeleteDoc) return deleteVaultDoc(inspectorWorldId(), el.dataset.vaultDeleteDoc);
    if (el.dataset.githubAdd) return connectGithubRepo(el.dataset.githubAdd);
    if (el.dataset.githubSync) return syncGithubRepo(el.dataset.worldId, el.dataset.githubSync);
    if (el.dataset.githubUnlink) return unlinkGithubRepo(el.dataset.worldId, el.dataset.githubUnlink);
    if (el.dataset.goalDone) return markGoalDone(el.dataset.goalDone);
  });

  root.addEventListener("submit", e => {
    const form = e.target;
    if (!(form instanceof HTMLFormElement)) return;
    const handlers = {
      "world-create-form": createWorldFromForm,
      "crm-create-form": submitCrmContact,
      "goal-create-form": submitGoal,
      "reminder-create-form": submitReminder,
      "agent-config-form": saveAgentConfig,
      "world-edit-form": saveWorldEdit,
      "vault-doc-form": submitVaultDoc,
    };
    if (handlers[form.id]) {
      e.preventDefault();
      handlers[form.id](form);
    }
  });

  root.addEventListener("change", e => {
    if (e.target.id === "chat-file") return uploadFile(e);
    if (e.target.id === "specialist-select-agents") return selectSpecialist(e.target.value);
    if (e.target.id === "rag-mode-select") {
      state.ragMode = e.target.value || "auto";
      localStorage.setItem("fos_rag_mode", state.ragMode);
      return;
    }
    if (e.target.matches("[data-crm-status]")) {
      updateCrmStatus(e.target.dataset.crmStatus, e.target.value);
    }
  });

  root.addEventListener("keydown", e => {
    if (e.target.id === "chat-input" && e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChat();
    }
    if (e.target.id === "memory-q" && e.key === "Enter") searchMemory();
  });

  root.addEventListener("input", e => {
    if (e.target.id === "delegate-selected") state._delegateDraft = e.target.value;
  });
}

async function refreshInfraHealth() {
  const btn = document.getElementById("btn-infra-refresh");
  if (btn) btn.disabled = true;
  try {
    state._infraHealth = await api("/infrastructure/health");
    render();
    afterRender();
  } catch (e) {
    console.error("Infrastructure health check failed:", e);
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function logoutPin() {
  try {
    await api("/auth/logout", { method: "POST", body: "{}" });
  } catch (_) { /* ignore */ }
  showPinGate();
}

async function createWorldFromForm(form) {
  const fd = new FormData(form);
  const name = (fd.get("name") || "").toString().trim();
  if (!name) return;
  try {
    const res = await api("/worlds", {
      method: "POST",
      body: JSON.stringify({
        name,
        kind: (fd.get("kind") || "project").toString(),
        template: (fd.get("template") || "").toString().trim() || undefined,
        description: (fd.get("description") || "").toString().trim(),
        context: (fd.get("context") || "").toString().trim(),
        repo_path: (fd.get("repo_path") || "").toString().trim(),
        github_repo: (fd.get("github_repo") || "").toString().trim(),
      }),
    });
    state.worlds = res.tree;
    setActiveWorld(res.world?.id);
    selectInspectorWorld(res.world?.id);
    await refresh();
    if (currentView === "world") {
      state._worldFull = await api("/graph/world");
      state._worldPreviews = state._worldFull?.world_previews || {};
      render();
    }
    form.reset();
    if (state.ui) state.ui.worldCreateOpen = false;
  } catch (e) { alert(e.message); }
}

async function submitCrmContact(form) {
  const fd = new FormData(form);
  const name = (fd.get("name") || "").toString().trim();
  if (!name) return;
  try {
    await api("/crm/contacts", {
      method: "POST",
      body: JSON.stringify({
        name,
        company: (fd.get("company") || "").toString().trim(),
        role: (fd.get("role") || "").toString().trim(),
        email: (fd.get("email") || "").toString().trim(),
        status: (fd.get("status") || "prospect").toString(),
        linkedin_url: (fd.get("linkedin_url") || "").toString().trim(),
        notes: (fd.get("notes") || "").toString().trim(),
      }),
    });
    state._crm = await api("/crm/contacts");
    if (state.ui) state.ui.crmFormOpen = false;
    await refresh();
    render();
    form.reset();
  } catch (e) { alert(e.message); }
}

async function updateCrmStatus(cid, status) {
  if (!cid || !status) return;
  try {
    await api(`/crm/contacts/${encodeURIComponent(cid)}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    state._crm = await api("/crm/contacts");
    await refresh();
    render();
  } catch (e) { alert(e.message); }
}

async function submitGoal(form) {
  const fd = new FormData(form);
  const title = (fd.get("title") || "").toString().trim();
  if (!title) return;
  try {
    await api("/goals", {
      method: "POST",
      body: JSON.stringify({
        title,
        detail: (fd.get("detail") || "").toString().trim(),
        priority: parseInt(fd.get("priority") || "3", 10) || 3,
      }),
    });
    state._goals = await api("/goals");
    if (state.ui) state.ui.goalsFormOpen = false;
    await refresh();
    render();
    form.reset();
  } catch (e) { alert(e.message); }
}

async function markGoalDone(gid) {
  if (!gid) return;
  try {
    await api(`/goals/${encodeURIComponent(gid)}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "done" }),
    });
    state._goals = await api("/goals");
    await refresh();
    render();
  } catch (e) { alert(e.message); }
}

async function submitReminder(form) {
  const fd = new FormData(form);
  const text = (fd.get("text") || "").toString().trim();
  const dueRaw = (fd.get("due_at") || "").toString().trim();
  if (!text || !dueRaw) return;
  const due_at = dueRaw.length === 16 ? `${dueRaw}:00` : dueRaw;
  try {
    await api("/reminders", {
      method: "POST",
      body: JSON.stringify({ text, due_at }),
    });
    state._goals = await api("/goals");
    if (state.ui) state.ui.reminderFormOpen = false;
    render();
    form.reset();
  } catch (e) { alert(e.message); }
}

async function saveAgentConfig(form) {
  const fd = new FormData(form);
  try {
    const res = await api("/agent/config", {
      method: "POST",
      body: JSON.stringify({
        autonomy_level: (fd.get("autonomy_level") || "balanced").toString(),
        auto_approve: fd.get("auto_approve") === "1",
      }),
    });
    state.config = { ...(state.config || {}), ...res };
    updateStatus();
    render();
  } catch (e) { alert(e.message); }
}

async function saveWorldEdit(form) {
  const id = form.dataset.worldId;
  if (!id) return;
  const fd = new FormData(form);
  const payload = {
    name: (fd.get("name") || "").toString().trim(),
    description: (fd.get("description") || "").toString(),
    context: (fd.get("context") || "").toString(),
  };
  if (id !== "root") {
    payload.kind = (fd.get("kind") || "project").toString();
    const tpl = (fd.get("template") || "").toString().trim();
    if (tpl) payload.template = tpl;
  }
  try {
    const res = await api(`/worlds/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    state.worlds = res.tree;
    state.worldEditing = null;
    if (currentView === "world") {
      state._worldFull = await api("/graph/world");
      state._worldPreviews = state._worldFull?.world_previews || {};
      await loadWorldVault(id);
      render();
    } else await refresh();
  } catch (e) { alert(e.message); }
}

async function submitVaultDoc(form) {
  const worldId = form.dataset.worldId;
  const docId = (form.querySelector("[name=doc_id]")?.value || "").trim();
  const fd = new FormData(form);
  const title = (fd.get("title") || "").toString().trim();
  const facetId = (fd.get("facet_id") || form.dataset.facetId || "docs").toString();
  const description = (fd.get("description") || "").toString().trim();
  const content = (fd.get("content") || "").toString();
  const file = form.querySelector('input[type="file"]')?.files?.[0];
  try {
    if (docId) {
      await api(`/worlds/${encodeURIComponent(worldId)}/vault/documents/${encodeURIComponent(docId)}`, {
        method: "PATCH",
        body: JSON.stringify({ title, description, facet_id: facetId, content: content || undefined }),
      });
    } else if (file) {
      const up = new FormData();
      up.append("file", file);
      up.append("title", title);
      up.append("description", description);
      up.append("facet_id", facetId);
      await apiUpload(`/worlds/${encodeURIComponent(worldId)}/vault/documents`, up);
    } else if (content.trim()) {
      await api(`/worlds/${encodeURIComponent(worldId)}/vault/documents`, {
        method: "POST",
        body: JSON.stringify({ title, description, facet_id: facetId, content }),
      });
    } else {
      return alert("Upload a file or paste markdown content.");
    }
    if (state.ui) {
      state.ui.vaultDocForm = false;
      state.ui.vaultDocEdit = null;
    }
    await loadWorldVault(worldId);
    render();
  } catch (e) { alert(e.message); }
}

async function startVaultDocEdit(worldId, docId) {
  if (!state.ui) state.ui = {};
  try {
    const res = await api(`/worlds/${encodeURIComponent(worldId)}/vault/documents/${encodeURIComponent(docId)}/content`);
    state.ui.vaultDocEdit = res.document;
    state.ui.vaultDocForm = true;
    state.ui.vaultFacet = res.document?.facet_id || state.ui.vaultFacet;
    render();
    const ta = $("#vault-doc-content");
    if (ta) ta.value = res.content || "";
  } catch (e) { alert(e.message); }
}

async function connectGithubRepo(worldId) {
  const full_name = $("#github-repo-pick")?.value?.trim();
  if (!full_name) return alert("Select a repository");
  const btn = document.querySelector(`[data-github-add="${worldId}"]`);
  if (btn) btn.disabled = true;
  try {
    const res = await api(`/worlds/${encodeURIComponent(worldId)}/repos`, {
      method: "POST",
      body: JSON.stringify({ full_name }),
      timeoutMs: 120000,
    });
    if (res.job?.status === "failed") throw new Error(res.job.message || "Could not start sync");
    if (res.job?.id) {
      await runGithubSyncJob(res.job.id, `Syncing ${full_name}`, { worldId, linkId: res.repo?.id });
    } else {
      await loadWorldVault(worldId);
      render();
    }
  } catch (e) {
    alert(e.message);
  } finally {
    if (btn) btn.disabled = state._syncingLinkIds.size > 0;
  }
}

async function syncGithubRepo(worldId, linkId) {
  if (isLinkSyncing(linkId)) return;
  try {
    const res = await api(`/worlds/${encodeURIComponent(worldId)}/repos/${encodeURIComponent(linkId)}/sync`, {
      method: "POST",
      body: "{}",
      timeoutMs: 120000,
    });
    if (res.job?.status === "failed") throw new Error(res.job.message || "Could not start sync");
    if (res.job?.id) {
      const name = (state._worldVault?.github_repos || []).find(r => String(r.id) === String(linkId))?.full_name || "repository";
      await runGithubSyncJob(res.job.id, `Re-syncing ${name}`, { worldId, linkId });
    }
  } catch (e) {
    alert(e.message);
  }
}

async function unlinkGithubRepo(worldId, linkId) {
  if (!confirm("Unlink this repo and remove its synced documents from this world?")) return;
  try {
    await api(`/worlds/${encodeURIComponent(worldId)}/repos/${encodeURIComponent(linkId)}`, { method: "DELETE" });
    await loadWorldVault(worldId);
    render();
  } catch (e) { alert(e.message); }
}

async function deleteVaultDoc(worldId, docId) {
  if (!confirm("Remove this document from the knowledge graph?")) return;
  try {
    await api(`/worlds/${encodeURIComponent(worldId)}/vault/documents/${encodeURIComponent(docId)}`, { method: "DELETE" });
    await loadWorldVault(worldId);
    render();
  } catch (e) { alert(e.message); }
}

async function vaultIngest(worldId) {
  try {
    const res = await api(`/worlds/${encodeURIComponent(worldId)}/vault/ingest`, { method: "POST", body: "{}" });
    alert(`Ingested ${res.files || 0} files (${res.total_chunks || 0} chunks)`);
    await loadWorldVault(worldId);
    render();
  } catch (e) { alert(e.message); }
}

async function vaultLinkRepo(worldId) {
  const path = $("#vault-repo-path")?.value?.trim();
  if (!path) return alert("Enter a local repo path");
  try {
    const res = await api(`/worlds/${encodeURIComponent(worldId)}/vault/link-repo`, {
      method: "POST",
      body: JSON.stringify({ repo_path: path }),
    });
    if (res.error) return alert(res.error);
    alert(`Linked and ingested ${res.files || 0} files`);
    await loadWorldVault(worldId);
    await refresh();
    render();
  } catch (e) { alert(e.message); }
}

async function vaultSearch(worldId) {
  const q = $("#vault-search-q")?.value?.trim();
  if (!q) return;
  const out = $("#vault-search-results");
  try {
    const res = await api(`/vault/search?${new URLSearchParams({ q, world_id: worldId })}`);
    const text = (res.hits || []).map(h =>
      `[${h.metadata?.domain || "?"}] ${h.metadata?.source || ""}\n${(h.text || "").slice(0, 200)}`
    ).join("\n\n---\n\n") || "No hits.";
    if (out) { out.textContent = text; out.hidden = false; }
  } catch (e) { if (out) { out.textContent = e.message; out.hidden = false; } }
}

async function deleteWorld(id) {
  if (!confirm("Delete this sub-world?")) return;
  try {
    const res = await api(`/worlds/${encodeURIComponent(id)}`, { method: "DELETE" });
    state.worlds = res.tree;
    if (currentWorldId() === id) setActiveWorld("root");
    if (inspectorWorldId() === id) selectInspectorWorld("root");
    await refresh();
    if (currentView === "world") {
      state._worldFull = await api("/graph/world");
      state._worldPreviews = state._worldFull?.world_previews || {};
      render();
    }
  } catch (e) { alert(e.message); }
}

function selectSpecialist(id) {
  const value = id || "";
  state.selectedSpecialist = value;
  localStorage.setItem("fos_selected_specialist", value);
  populateSpecialistSelect();
  render();
}

async function agentsVaultSearch() {
  const q = $("#agents-vault-q")?.value?.trim();
  state._agentsVaultQ = q;
  const out = $("#agents-vault-results");
  const wid = currentWorldId();
  if (!q || !wid || wid === "root") return;
  try {
    const res = await api(`/vault/search?${new URLSearchParams({ q, world_id: wid })}`);
    const text = (res.hits || []).map(h =>
      `[${h.metadata?.domain || "?"}] ${h.metadata?.source || ""}\n${(h.text || "").slice(0, 240)}`
    ).join("\n\n---\n\n") || "No hits.";
    if (out) { out.textContent = text; out.hidden = false; }
  } catch (e) {
    if (out) { out.textContent = e.message; out.hidden = false; }
  }
}

async function delegateAgent() {
  const specId = currentSpecialistId();
  const ta = $("#delegate-selected");
  const task = (ta?.value || "").trim();
  if (!task) return;
  const btn = $("#delegate-selected-btn");
  const meta = routingMeta(state._agents || {});
  const direct = !!specId;
  const started = Date.now();
  if (btn) { btn.disabled = true; btn.textContent = "Running…"; }
  startLivePoll();
  state.agentsTab = "live";
  localStorage.setItem("fos_agents_tab", "live");
  try {
    let result;
    if (!direct) {
      const res = await api("/chat", {
        method: "POST",
        body: JSON.stringify({ message: task, world_id: currentWorldId(), rag_mode: currentRagMode() }),
      });
      result = res.reply || "(no response)";
      if (res.new_approvals?.length) {
        state.approvals = res.pending_approvals;
        updateBadges();
      }
    } else {
      const res = await api("/agents/delegate", {
        method: "POST",
        body: JSON.stringify({ specialist: specId, task, world_id: currentWorldId() }),
      });
      result = typeof res.result === "string" ? res.result : JSON.stringify(res, null, 2);
    }
    state._delegateResult = result;
    state._delegateDraft = "";
    if (ta) ta.value = "";
    const runId = `local-${started}`;
    persistAgentRun({
      id: runId,
      agent: direct ? specId : "supervisor",
      task,
      result,
      duration_s: Math.round((Date.now() - started) / 1000),
      ts: Math.floor(started / 1000),
      tools: [],
      source: "local",
    });
    state.agentsTab = "runs";
    localStorage.setItem("fos_agents_tab", "runs");
    state.expandedRunId = runId;
  } catch (e) {
    state._delegateResult = "Error: " + e.message;
  }
  if (btn) {
    btn.disabled = false;
    btn.textContent = direct ? `Run ${meta.label}` : "Send to supervisor";
  }
  try {
    const runs = await api("/agents/runs");
    state._agentRunsApi = runs.runs || [];
    state._agentActions = runs.actions || [];
  } catch (_) {}
  pollLive();
  render();
  drawGraphs();
}

async function sendChat() {
  const input = $("#chat-input");
  const text = (input?.value || "").trim();
  if (!text) return;
  const specId = currentSpecialistId();
  const meta = routingMeta(state._agents || {});
  const direct = !!specId;
  input.value = "";
  chatHistory.push({ role: "user", text });
  localStorage.setItem("fos_chat", JSON.stringify(chatHistory));
  render();
  animateLatestChatMessage();
  const btn = $("#chat-send");
  const btnLabel = direct ? `Run ${meta.label}` : "Send";
  if (btn) { btn.disabled = true; btn.textContent = "…"; }
  startLivePoll();
  const pollDuring = setInterval(pollLive, 800);
  try {
    if (!direct) {
      const res = await api("/chat", {
        method: "POST",
        body: JSON.stringify({ message: text, world_id: currentWorldId(), rag_mode: currentRagMode() }),
      });
      chatHistory.push({ role: "agent", text: res.reply || "(no response)" });
      if (res.new_approvals?.length) {
        state.approvals = res.pending_approvals;
        updateBadges();
      }
    } else {
      const res = await api("/agents/delegate", {
        method: "POST",
        body: JSON.stringify({ specialist: specId, task: text, world_id: currentWorldId() }),
      });
      const reply = typeof res.result === "string" ? res.result : JSON.stringify(res, null, 2);
      chatHistory.push({ role: "agent", text: reply });
      persistAgentRun({
        id: `local-chat-${Date.now()}`,
        agent: specId,
        task: text,
        result: reply,
        duration_s: 0,
        ts: Math.floor(Date.now() / 1000),
        tools: [],
        source: "chat",
      });
    }
    localStorage.setItem("fos_chat", JSON.stringify(chatHistory));
  } catch (e) {
    chatHistory.push({ role: "system", text: "Error: " + e.message });
    localStorage.setItem("fos_chat", JSON.stringify(chatHistory));
  }
  clearInterval(pollDuring);
  pollLive();
  if (btn) { btn.disabled = false; btn.textContent = btnLabel; }
  render();
  animateLatestChatMessage();
}

async function uploadFile(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  chatHistory.push({ role: "user", text: `📎 Uploaded: ${file.name}` });
  render();
  try {
    fd.append("world_id", currentWorldId());
    const r = await fetch("/api/upload", { method: "POST", body: fd, credentials: "same-origin" });
    const res = await r.json().catch(() => ({}));
    if (r.status === 401 && res.pin_required) {
      showPinGate();
      throw new Error("Enter your PIN to continue");
    }
    if (!r.ok) throw new Error(res.error || r.statusText);
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
  const mob = $("#mobile-approval-badge");
  if (mob) { mob.textContent = n; mob.hidden = !n; }
  const mobMenu = $("#mobile-menu-approval-badge");
  if (mobMenu) { mobMenu.textContent = n; mobMenu.hidden = !n; }
  const unr = state.unread_notifications || 0;
  const nb2 = $("#notif-badge");
  if (nb2) { nb2.textContent = unr; nb2.hidden = !unr; }
}

function setConnectionStatus(label, kind = "ok") {
  const dot = $("#status-dot");
  const txt = $("#status-text");
  const mobDot = $("#mobile-status-dot");
  const mobTxt = $("#mobile-status-text");
  if (txt) txt.textContent = label;
  if (mobTxt) mobTxt.textContent = label;
  dot?.classList.toggle("ok", kind === "ok");
  dot?.classList.toggle("paused", kind !== "ok");
  mobDot?.classList.toggle("ok", kind === "ok");
  mobDot?.classList.toggle("paused", kind !== "ok");
}

function updateStatus() {
  const c = state.config || {};
  if (c.agent_paused) setConnectionStatus("Agent paused", "paused");
  else setConnectionStatus("Online", "ok");
  const sub = $("#brand-sub");
  if (sub) sub.textContent = c.my_name || c.company_name || APP_NAME;
  document.title = c.my_name ? `${APP_NAME} — ${c.my_name}` : APP_NAME;
}

function showBootError(err) {
  console.error(`${APP_NAME} boot failed:`, err);
  setConnectionStatus("Offline", "paused");
  const msg = esc(err?.message || String(err));
  $("#content").innerHTML = `<div class="driver-card span-12">
    <p class="title-md">Could not connect to ${esc(APP_NAME)}</p>
    <p class="body-md muted" style="margin-top:8px">${msg}</p>
    <p class="body-md muted" style="margin-top:12px">Make sure <code>python main.py</code> is running, then tap <strong>Refresh</strong> in the top bar.</p>
  </div>`;
}

async function refresh() {
  const prevWorld = state.activeWorldId;
  const prevSpec = state.selectedSpecialist;
  const prevUi = state.ui;
  state = { ...state, ...(await api("/state")) };
  state.activeWorldId = prevWorld || state.activeWorldId || "root";
  state.selectedSpecialist = prevSpec ?? state.selectedSpecialist ?? "";
  state.ui = prevUi || state.ui;
  try {
    populateWorldSelect();
    populateSpecialistSelect();
  } catch (e) {
    console.error("populate selects failed:", e);
  }
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
$("#btn-sidebar-open")?.addEventListener("click", openSidebar);
$("#sidebar-close")?.addEventListener("click", closeMobileShell);
$("#sidebar-backdrop")?.addEventListener("click", closeMobileShell);
document.querySelectorAll(".mobile-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    const v = tab.dataset.mobileView;
    if (v === "more") {
      syncMobileNav(currentView);
      document.getElementById("mobile-menu-drawer")?.showModal();
    } else {
      goView(v);
    }
  });
});
document.querySelectorAll(".mobile-menu-link").forEach(b => {
  b.addEventListener("click", () => goView(b.dataset.view));
});
const mobileMenuDrawer = $("#mobile-menu-drawer");
$("#mobile-menu-close")?.addEventListener("click", () => mobileMenuDrawer?.close());
mobileMenuDrawer?.addEventListener("click", (e) => {
  if (e.target === mobileMenuDrawer) mobileMenuDrawer.close();
});
$("#btn-refresh")?.addEventListener("click", () => refresh().then(render));
window.addEventListener("resize", () => {
  if (window.innerWidth > 900) closeMobileShell();
});
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

$("#world-select")?.addEventListener("change", e => {
  setActiveWorld(e.target.value);
  if (currentView === "world" || currentView === "chat" || currentView === "agents") render();
});

window.addEventListener("error", (e) => {
  console.error("UI error:", e.error || e.message);
  if (!state?.config?.my_name) setConnectionStatus("UI error — hard refresh", "paused");
});

async function loadBootExtras() {
  const [agents, world] = await Promise.all([
    api("/agents").catch(() => ({})),
    api("/world").catch(() => ({})),
  ]);
  state._agents = agents?.specialists?.length ? agents : { ...agents, specialists: agents.specialists || DEFAULT_SPECIALISTS };
  state._world = world || {};
  if (!state.worlds?.root && world?.worlds) state.worlds = world.worlds;
  populateWorldSelect();
  populateSpecialistSelect();
  await loadGraphData();
  render();
}

function showPinGate(message, lockedSeconds) {
  const gate = $("#pin-gate");
  const app = document.querySelector(".app");
  const err = $("#pin-error");
  const input = $("#pin-input");
  if (gate) {
    gate.hidden = false;
    gate.classList.add("is-visible");
  }
  if (app) app.setAttribute("inert", "");
  if (err) {
    if (message) {
      err.textContent = message;
      err.hidden = false;
    } else {
      err.hidden = true;
      err.textContent = "";
    }
  }
  if (input && !lockedSeconds) {
    input.disabled = false;
    input.focus();
  }
  if (input && lockedSeconds) {
    input.disabled = true;
    if (err) {
      err.textContent = `Too many attempts. Wait ${lockedSeconds}s.`;
      err.hidden = false;
    }
  }
  setConnectionStatus("Locked", "paused");
}

function hidePinGate() {
  const gate = $("#pin-gate");
  const app = document.querySelector(".app");
  if (gate) {
    gate.hidden = true;
    gate.classList.remove("is-visible");
  }
  if (app) app.removeAttribute("inert");
}

async function fetchAuthStatus() {
  const r = await fetch("/api/auth/status", { credentials: "same-origin", headers: { Accept: "application/json" } });
  return r.json();
}

function bindPinGate() {
  if (window.__FOS_PIN_BOUND) return;
  window.__FOS_PIN_BOUND = true;
  $("#pin-form")?.addEventListener("submit", async e => {
    e.preventDefault();
    const pin = ($("#pin-input")?.value || "").trim();
    const err = $("#pin-error");
    if (!/^\d{6}$/.test(pin)) {
      if (err) { err.textContent = "Enter exactly 6 digits"; err.hidden = false; }
      return;
    }
    try {
      const res = await fetch("/api/auth/pin", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || "Incorrect PIN");
      hidePinGate();
      $("#pin-input").value = "";
      if (err) err.hidden = true;
      await startApp();
    } catch (ex) {
      if (err) { err.textContent = ex.message; err.hidden = false; }
      const st = await fetchAuthStatus().catch(() => ({}));
      if (st.locked_seconds) showPinGate(ex.message, st.locked_seconds);
    }
  });
  $("#pin-input")?.addEventListener("input", e => {
    e.target.value = e.target.value.replace(/\D/g, "").slice(0, 6);
  });
}

function applyBootUrlParams() {
  const p = new URLSearchParams(location.search);
  const view = p.get("view");
  const world = p.get("world");
  if (view) currentView = view;
  if (world) {
    state.inspectorWorldId = world;
    setActiveWorld(world);
  }
  if (p.get("github") === "connected" || p.get("github_error")) {
    const err = p.get("github_error");
    if (err) console.warn("GitHub auth:", err);
    history.replaceState({}, "", location.pathname);
  }
}

async function startApp() {
  try {
    await refresh();
  } catch (e) {
    showBootError(e);
    return;
  }
  applyBootUrlParams();
  syncMobileNav(currentView);
  render();
  if (currentView === "world") {
    loadViewData("world").then(() => { render(); afterRender(); }).catch(console.error);
  }
  startLivePoll();
  try {
    await loadBootExtras();
  } catch (e) {
    console.error("boot extras failed:", e);
  }
}

async function boot() {
  initContentDelegation();
  bindPinGate();
  let auth = window.__FOS_AUTH;
  if (!auth) {
    try {
      auth = await fetchAuthStatus();
    } catch (e) {
      showBootError(e);
      return;
    }
  }
  if (auth.pin_required && !auth.authenticated) {
    showPinGate(null, auth.locked_seconds || 0);
    return;
  }
  hidePinGate();
  await startApp();
}

boot();

setInterval(() => refresh().then(() => {
  updateBadges();
  updateStatus();
}).catch((e) => {
  console.error(e);
  setConnectionStatus("Reconnecting…", "paused");
}), 30000);
