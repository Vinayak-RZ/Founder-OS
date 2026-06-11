/* Founder OS Web UI */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

let state = {
  live: {},
  selectedAgent: localStorage.getItem("fos_selected_agent") || "pulse",
  activeWorldId: localStorage.getItem("fos_active_world") || "root",
};
let currentView = "dashboard";
let chatHistory = JSON.parse(localStorage.getItem("fos_chat") || "[]");
let livePollTimer = null;
let memoryGraphTab = "graph";
let worldGraphTab = "hierarchy";
let lastLiveActive = false;

const TITLES = {
  dashboard: "Command center",
  chat: "Chat",
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

const CHART_COLORS = ["#f75440", "#00666b", "#03904a", "#051f13", "#5a403c", "#8f706b", "#e3beb8"];

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

function ownerLabel() {
  const c = state.config || {};
  return c.my_name ? `${c.my_name}'s Founder OS` : "Founder OS";
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
  const actor = live?.active ? live.actor : "";
  if (agentId === "supervisor") return actor === "user";
  return actor === `subagent:${agentId}` || actor.includes(agentId);
}

const AGENT_ROLES = {
  aggregator: { label: "Aggregator", cls: "agent-role--aggregator" },
  outreach: { label: "Outreach", cls: "agent-role--outreach" },
  leads: { label: "Leads", cls: "agent-role--leads" },
  research: { label: "Intel", cls: "agent-role--research" },
  knowledge: { label: "Vault", cls: "agent-role--vault" },
};

function agentRoleBadge(role) {
  const m = AGENT_ROLES[role] || { label: role || "Specialist", cls: "" };
  return `<span class="agent-role-badge ${m.cls}">${esc(m.label)}</span>`;
}

function renderAgentCards(agents, live, selectable = false) {
  const sup = agents?.supervisor || {};
  const specs = agents?.specialists || [];
  const sel = state.selectedAgent;
  const cards = [
    { id: "supervisor", label: "Supervisor", role: "aggregator", brief: sup.role || "Orchestrates specialists", tool_count: agents?.total_tools, categories: ["orchestration"], delegate: false, skills: [] },
    ...specs.map(s => ({ ...s, label: s.label || s.id, delegate: true })),
  ];
  return `<div class="agent-grid">${cards.map(a => {
    const isBusy = agentBusy(live, a.id);
    const isSel = selectable && a.delegate && sel === a.id;
    const inner = `
      <div class="agent-card-head">
        <h3>${esc(a.label)}</h3>
        <span class="agent-status ${isBusy ? "busy" : "ready"}">${isBusy ? "Working" : "Ready"}</span>
      </div>
      ${a.role ? agentRoleBadge(a.role) : ""}
      <p>${esc((a.brief || "").slice(0, 160))}</p>
      ${(a.skills || []).length ? `<p class="agent-meta">Skills: ${esc(a.skills.join(", "))}</p>` : ""}
      <p class="agent-meta">${a.tool_count != null ? `${a.tool_count} tools` : ""}${a.categories ? ` · ${esc((a.categories || []).join(", "))}` : ""}</p>
      ${a.delegate && selectable ? `<p class="world-meta" style="margin-top:8px">${isSel ? "Selected for delegation" : "Click to select"}</p>` : ""}
      ${!a.delegate ? `<p class="world-meta" style="margin-top:8px">Use Chat to message</p>` : ""}`;
    if (selectable && a.delegate) {
      return `<button type="button" class="agent-card agent-card-selectable${isBusy ? " is-busy" : ""}${isSel ? " is-selected" : ""}" data-select-agent="${esc(a.id)}">${inner}</button>`;
    }
    return `<article class="agent-card${isBusy ? " is-busy" : ""}">${inner}</article>`;
  }).join("")}</div>`;
}

function selectedAgentMeta(agents) {
  const specs = agents?.specialists || [];
  return specs.find(s => s.id === state.selectedAgent) || specs[0] || { id: "pulse", label: "Pulse" };
}

function drawGraphs() {
  if (currentView === "dashboard" && state._runtimeGraph) {
    FOSGraph.render("graph-runtime-dash", state._runtimeGraph, { layout: { name: "breadthfirst", directed: true, padding: 20 } });
  }
  if (currentView === "agents" && state._runtimeGraph) {
    FOSGraph.render("graph-runtime-agents", state._runtimeGraph);
  }
  if (currentView === "world") {
    const graph = worldGraphTab === "ecosystem"
      ? state._worldGraph
      : (state._worldHierarchyGraph || state._worldGraph);
    if (graph) {
      FOSGraph.render("graph-world", graph, {
        layout: worldGraphTab === "hierarchy" ? FOSGraph.HIERARCHY_LAYOUT : FOSGraph.LAYOUT,
        onSelect: (d) => {
          if (d.world_id) selectInspectorWorld(d.world_id);
        },
      });
      FOSGraph.highlightWorld("graph-world", inspectorWorldId(), currentWorldId());
    }
  }
  if (currentView === "memory" && state._memoryGraph) {
    FOSGraph.render("graph-memory", state._memoryGraph, {
      onSelect: (d) => {
        const el = $("#graph-memory-detail");
        if (el) el.textContent = `${d.type}: ${d.label}`;
      },
    });
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

function drawDashboardCharts() {
  const tools = state._world?.tools_by_category || state.about?.tools_by_category || {};
  const entries = Object.entries(tools).slice(0, 8);
  if (entries.length && $("#chart-tools")) {
    FOSCharts.bar("chart-tools", entries.map(([k]) => k), entries.map(([, v]) => v), { colors: CHART_COLORS });
  }
  const crm = state.snapshot?.crm?.by_status || {};
  const segs = Object.entries(crm).map(([k, v]) => ({ label: k, value: v }));
  if (segs.length && $("#chart-crm")) {
    FOSCharts.donut("chart-crm", segs, { centerLabel: "contacts", colors: CHART_COLORS });
  }
  const hist = [...(state.usage_history || [])].reverse();
  if (hist.length && $("#chart-usage")) {
    FOSCharts.spark("chart-usage", hist.map(h => h.llm_calls || h.calls || 0));
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
      if (currentView === "dashboard") FOSGraph.update("graph-runtime-dash", state._runtimeGraph);
      if (currentView === "agents") FOSGraph.update("graph-runtime-agents", state._runtimeGraph);
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
    ? `<div class="spec-cell race-position-cell"><dt>Approvals</dt><dd>${pending}</dd></div>`
    : `<div class="spec-cell"><dt>Approvals</dt><dd>0</dd></div>`;
  const live = state.live || {};
  const agents = state._agents || {};

  return `
    <header class="hero-band-cinema command-hero">
      <p class="section-eyebrow">${esc(cfg.company_name || "Your startup")}</p>
      <h2 class="hero-title"><span class="hero-owner">${esc(ownerLabel())}</span></h2>
      <p class="body-md" style="max-width:52ch">Operate ${esc(cfg.company_name || "your startup")}, research new ideas, and run specialists — all from one console.</p>
      <div class="hero-actions">
        <button type="button" class="button-primary" data-goto="chat">Message supervisor</button>
        <button type="button" class="button-outline-on-dark" data-goto="agents">Delegate to agents</button>
        ${pending > 0 ? `<button type="button" class="button-outline-on-dark" data-goto="approvals">Approvals (${pending})</button>` : ""}
      </div>
    </header>
    <div class="dashboard-grid">
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
        </dl>` : `<p class="body-md" style="margin-top:var(--space-sm)">Share cash, burn, and MRR in chat to track runway.</p>`}
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
  const meta = selectedAgentMeta(agents);
  const draft = state._delegateDraft || "";
  const skills = agents.skills || [];
  return `
    <section class="aggregator-hero driver-card" style="margin-bottom:var(--space-md)">
      <p class="section-eyebrow">Command aggregator</p>
      <h2 class="hero-title" style="font-size:1.35rem;margin:var(--space-xxs) 0">Track parallel work — don't replace Cursor</h2>
      <p class="body-md" style="max-width:62ch">Founder OS surfaces status across worlds, linked doc repos, CRM, and outreach. Deep research and coding stay in your other setups; use <strong>Pulse</strong> for what's happening, <strong>Vault</strong> to query docs, <strong>Outreach</strong> for sends.</p>
      ${skills.length ? `<div class="skills-row">${skills.map(s =>
        `<span class="skill-chip${s.installed ? "" : " is-missing"}">${esc(s.name)}</span>`
      ).join("")}</div>` : ""}
    </section>
    <p class="body-md" style="max-width:60ch;margin-bottom:var(--space-md)">Select a specialist, describe a coordination task (not deep research), and run.</p>
    <div class="agents-layout">
      <div>
        ${renderLivePanel(live, "agents-live-panel")}
        <p class="caption-uppercase" style="margin-top:var(--space-md)">Select agent</p>
        <div style="margin-top:var(--space-sm)">${renderAgentCards(agents, live, true)}</div>
        <p class="caption-uppercase" style="margin-top:var(--space-md)">How it's running</p>
        <div id="graph-runtime-agents" class="graph-canvas" style="margin-top:var(--space-xs)"></div>
      </div>
      <aside class="delegate-panel">
        <p class="caption-uppercase">Delegate task</p>
        <h3>${esc(meta.label)}</h3>
        <p class="world-meta">World: ${esc(activeWorldLabel())}</p>
        <p class="body-md" style="margin:var(--space-xxs) 0 var(--space-sm)">${esc((meta.brief || "").slice(0, 200))}</p>
        <div class="agent-delegate">
          <textarea class="text-input-on-dark" id="delegate-selected" placeholder="What should ${esc(meta.label)} do?">${esc(draft)}</textarea>
          <button type="button" class="button-primary" id="delegate-selected-btn">Run ${esc(meta.label)}</button>
        </div>
        <pre class="delegate-result mono" id="delegate-result-selected" ${state._delegateResult ? "" : "hidden"}>${esc(state._delegateResult || "")}</pre>
      </aside>
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
    return;
  }
  try {
    const res = await api(`/worlds/${encodeURIComponent(worldId)}/vault`);
    state._worldVault = res.vault || null;
  } catch (_) {
    state._worldVault = null;
  }
}

function selectInspectorWorld(id) {
  state.inspectorWorldId = id || "root";
  if (currentView === "world") {
    state._motionSkipOnce = true;
    loadWorldVault(id).then(() => {
      render();
      FOSMotion?.flashElement?.($("#world-inspector"));
      FOSGraph.highlightWorld("graph-world", inspectorWorldId(), currentWorldId());
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
          <label>Kind
            <select class="text-input-on-dark" name="kind">
              <option value="project"${w.kind === "project" ? " selected" : ""}>Project / startup</option>
              <option value="idea"${w.kind === "idea" ? " selected" : ""}>Idea</option>
              <option value="research"${w.kind === "research" ? " selected" : ""}>Research</option>
              <option value="technical"${w.kind === "technical" ? " selected" : ""}>Technical project</option>
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

function renderWorldVaultPanel(w) {
  if (!w || w.id === "root") return "";
  const vault = state._worldVault || {};
  const facets = vault.facets || [];
  const counts = vault.domain_counts || {};
  const cards = facets.map(f => `
    <article class="vault-facet-card">
      <div class="vault-facet-head">
        <h4>${esc(f.label)}</h4>
        <span class="world-meta">${esc(f.domain_label || f.domain)}</span>
      </div>
      <p class="world-meta">${esc(f.folder)}/ · ${f.file_count || 0} files · ${counts[f.domain] || 0} chunks indexed</p>
      <ul class="vault-file-list">${(f.files || []).slice(0, 5).map(file =>
        `<li class="mono">${esc(file.relative || file.name)}</li>`
      ).join("") || "<li class='muted'>No docs yet</li>"}</ul>
    </article>`).join("");
  return `
    <section class="driver-card vault-panel" style="margin-top:var(--space-md)">
      <div class="vault-panel-head">
        <div>
          <p class="section-eyebrow">Knowledge vault</p>
          <h3 class="title-sm">${esc(w.name)} documentation</h3>
          <p class="world-meta">${esc(vault.vault_path || "")}${vault.repo_path ? ` · linked: ${esc(vault.repo_path)}` : ""}</p>
        </div>
        <div class="vault-panel-actions">
          <input class="text-input-on-dark" id="vault-repo-path" placeholder="Local clone path (e.g. C:\\docs\\stamped-energy)" value="${esc(w.repo_path || "")}">
          <button type="button" class="button-outline-on-dark button-sm" data-vault-link="${esc(w.id)}">Link &amp; ingest</button>
          <button type="button" class="button-primary button-sm" data-vault-ingest="${esc(w.id)}">Re-ingest vault</button>
        </div>
      </div>
      <div class="vault-search-row">
        <input class="text-input-on-dark" id="vault-search-q" placeholder="Query this world's docs…">
        <button type="button" class="button-outline-on-dark button-sm" data-vault-search="${esc(w.id)}">Search</button>
      </div>
      <pre class="vault-search-results mono" id="vault-search-results" hidden></pre>
      <div class="vault-facet-grid">${cards || "<p class='body-md muted'>Loading vault…</p>"}</div>
    </section>`;
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

  return `
    <div class="worlds-page">
      <section class="worlds-hero">
        <div class="worlds-hero-lead">
          <h2>${esc(founder)}'s world map</h2>
          <p><strong>Aggregator view</strong> — track parallel ventures, link doc repos per world, query the vault. Deep work stays in Cursor; Founder OS surfaces status and outreach.</p>
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
            </div>
          </div>
          <div id="graph-world" class="graph-canvas world-graph-canvas" role="img" aria-label="World graph"></div>
          <div class="world-graph-legend">
            <span><i style="border-color:#051f13"></i> Main</span>
            <span><i style="border-color:#f75440"></i> Project</span>
            <span><i style="border-color:#ffb4a8"></i> Idea</span>
            <span><i style="border-color:#00666b"></i> Research</span>
            <span><i style="border-color:#f75440;background:#f7544033"></i> Active</span>
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

      <details class="world-create-drawer">
        <summary>Create sub-world <span class="muted">+</span></summary>
        <form class="world-form" id="world-create-form">
          <input class="text-input-on-dark" name="name" placeholder="Name — e.g. Stamped Energy" required>
          <select class="text-input-on-dark" name="kind">
            <option value="project">Startup / venture</option>
            <option value="technical">Technical project</option>
            <option value="idea">Idea</option>
            <option value="research">Research track</option>
          </select>
          <input class="text-input-on-dark" name="repo_path" placeholder="Optional: local docs repo path to link on create">
          <input class="text-input-on-dark" name="github_repo" placeholder="Optional: GitHub repo (owner/name) for reference">
          <input class="text-input-on-dark" name="description" placeholder="Short description">
          <textarea class="text-input-on-dark" name="context" rows="4" placeholder="What should the agent track in this world?"></textarea>
          <button type="submit" class="button-primary button-sm">Create world</button>
        </form>
      </details>
    </div>`;
}

function isRootWorld(w) {
  return !w || w.id === "root";
}

function renderChat() {
  const msgs = chatHistory.map(m =>
    `<div class="msg ${m.role}">${esc(m.text)}</div>`
  ).join("");
  const live = state.live || {};
  return `<div class="chat-layout">
    <div class="chat-wrap">
      <div class="chat-messages" id="chat-messages">${msgs || `<div class="msg system">Hi Vinayak — ask about ${esc(state.config?.company_name || "your startup")}, research ideas, CRM, outreach, or delegate from Agents.</div>`}</div>
      <p class="world-meta" style="margin-bottom:var(--space-xs)">Context: <strong>${esc(activeWorldLabel())}</strong></p>
      <div class="chat-input-row">
        <textarea class="text-input-on-dark chat-input" id="chat-input" placeholder="Message your supervisor…" rows="2"></textarea>
        <button class="button-primary" id="chat-send">Send</button>
      </div>
      <div class="chat-toolbar">
        <span class="badge-pill">World: ${esc(activeWorldLabel())}</span>
        <label class="button-outline-on-dark button-sm upload-label">Upload<input type="file" id="chat-file" hidden accept=".pdf,.docx,.txt,.md,.csv,.json"></label>
        <button type="button" class="button-outline-on-dark button-sm" id="chat-clear">Clear</button>
        <button type="button" class="button-outline-on-dark button-sm" data-goto="agents">Agents</button>
        <button type="button" class="button-outline-on-dark button-sm" data-goto="world">Worlds</button>
      </div>
    </div>
    ${renderLivePanel(live, "chat-live-panel")}
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
  if (view === "agents") state._agents = await api("/agents");
  if (view === "activity") state._activity = await api("/activity");
  if (view === "world") {
    state._worldFull = await api("/graph/world");
    state._worldPreviews = state._worldFull?.world_previews || {};
    if (!state.inspectorWorldId) state.inspectorWorldId = currentWorldId();
    await loadWorldVault(inspectorWorldId());
  }
  if (view === "memory") state._memoryFull = await api("/graph/memory");
  if (view === "dashboard") {
    state._agents = await api("/agents");
    state._world = await api("/world");
  }
  await loadGraphData();
}

function goView(view) {
  currentView = view;
  $$(".nav button").forEach(b => b.classList.toggle("is-active", b.dataset.view === view));
  $("#view-title").textContent = TITLES[view] || view;
  FOSMotion?.animateTopbarTitle?.();
  if (["dashboard", "agents", "chat", "activity", "world"].includes(view)) startLivePoll();
  else stopLivePoll();
  render();
  loadViewData(view).then(() => { render(); afterRender(); }).catch(console.error);
}

function afterRender() {
  if (currentView === "dashboard") drawDashboardCharts();
  drawGraphs();
  pollLive();
  if (state._motionSkipOnce) {
    state._motionSkipOnce = false;
  } else {
    FOSMotion?.runView?.(currentView);
  }
}

function animateLatestChatMessage() {
  requestAnimationFrame(() => {
    const msgs = $("#chat-messages")?.querySelectorAll(".msg:not(.system)");
    const last = msgs?.[msgs.length - 1];
    FOSMotion?.animateNewMessage?.(last);
  });
}

function render() {
  const fns = {
    dashboard: renderDashboard, chat: renderChat, agents: renderAgents,
    world: renderWorld, approvals: renderApprovals, crm: renderCrm, goals: renderGoals,
    memory: renderMemory, tools: renderTools, activity: renderActivity,
    settings: renderSettings,
  };
  $("#content").innerHTML = (fns[currentView] || renderDashboard)();
  document.querySelector(".content")?.classList.toggle("content--worlds", currentView === "world");
  bindViewEvents();
  afterRender();
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
  $$("[data-select-agent]").forEach(b => b.addEventListener("click", () => selectAgent(b.dataset.selectAgent)));
  $("#delegate-selected-btn")?.addEventListener("click", () => delegateAgent(state.selectedAgent));
  $("#delegate-selected")?.addEventListener("input", e => { state._delegateDraft = e.target.value; });
  $$("[data-memory-tab]").forEach(b => b.addEventListener("click", () => {
    memoryGraphTab = b.dataset.memoryTab;
    render();
  }));
  $("#world-create-form")?.addEventListener("submit", e => {
    e.preventDefault();
    createWorldFromForm(e.target);
  });
  $("#world-edit-form")?.addEventListener("submit", e => {
    e.preventDefault();
    saveWorldEdit(e.target);
  });
  $$("[data-inspect-world]").forEach(b => b.addEventListener("click", () => selectInspectorWorld(b.dataset.inspectWorld)));
  $$("[data-world-graph-tab]").forEach(b => b.addEventListener("click", () => {
    worldGraphTab = b.dataset.worldGraphTab;
    render();
  }));
  $$("[data-use-world]").forEach(b => b.addEventListener("click", () => {
    setActiveWorld(b.dataset.useWorld);
    goView("chat");
  }));
  $$("[data-set-active-world]").forEach(b => b.addEventListener("click", () => {
    setActiveWorld(b.dataset.setActiveWorld);
    render();
  }));
  $$("[data-edit-world]").forEach(b => b.addEventListener("click", () => {
    state.worldEditing = b.dataset.editWorld;
    render();
  }));
  $$("[data-cancel-edit]").forEach(b => b.addEventListener("click", () => {
    state.worldEditing = null;
    render();
  }));
  $$("[data-delete-world]").forEach(b => b.addEventListener("click", () => deleteWorld(b.dataset.deleteWorld)));
  $$("[data-vault-ingest]").forEach(b => b.addEventListener("click", () => vaultIngest(b.dataset.vaultIngest)));
  $$("[data-vault-link]").forEach(b => b.addEventListener("click", () => vaultLinkRepo(b.dataset.vaultLink)));
  $$("[data-vault-search]").forEach(b => b.addEventListener("click", () => vaultSearch(b.dataset.vaultSearch)));
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
  if (id !== "root") payload.kind = (fd.get("kind") || "project").toString();
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
      render();
    } else await refresh();
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

function selectAgent(id) {
  state.selectedAgent = id;
  localStorage.setItem("fos_selected_agent", id);
  render();
}

async function delegateAgent(id) {
  const ta = $("#delegate-selected");
  const task = (ta?.value || "").trim();
  if (!task) return;
  const btn = $("#delegate-selected-btn");
  const out = $("#delegate-result-selected");
  const meta = selectedAgentMeta(state._agents || {});
  if (btn) { btn.disabled = true; btn.textContent = "Running…"; }
  startLivePoll();
  try {
    const res = await api("/agents/delegate", {
      method: "POST",
      body: JSON.stringify({ specialist: id, task, world_id: currentWorldId() }),
    });
    state._delegateResult = typeof res.result === "string" ? res.result : JSON.stringify(res, null, 2);
    state._delegateDraft = "";
    if (out) { out.hidden = false; out.textContent = state._delegateResult; }
    if (ta) ta.value = "";
  } catch (e) {
    state._delegateResult = "Error: " + e.message;
    if (out) { out.hidden = false; out.textContent = state._delegateResult; }
  }
  if (btn) { btn.disabled = false; btn.textContent = `Run ${meta.label}`; }
  pollLive();
  render();
}

async function sendChat() {
  const input = $("#chat-input");
  const text = (input?.value || "").trim();
  if (!text) return;
  input.value = "";
  chatHistory.push({ role: "user", text });
  localStorage.setItem("fos_chat", JSON.stringify(chatHistory));
  render();
  animateLatestChatMessage();
  const btn = $("#chat-send");
  if (btn) { btn.disabled = true; btn.textContent = "…"; }
  startLivePoll();
  const pollDuring = setInterval(pollLive, 800);
  try {
    const res = await api("/chat", {
      method: "POST",
      body: JSON.stringify({ message: text, world_id: currentWorldId() }),
    });
    chatHistory.push({ role: "agent", text: res.reply || "(no response)" });
    localStorage.setItem("fos_chat", JSON.stringify(chatHistory));
    if (res.new_approvals?.length) {
      state.approvals = res.pending_approvals;
      updateBadges();
    }
  } catch (e) {
    chatHistory.push({ role: "system", text: "Error: " + e.message });
  }
  clearInterval(pollDuring);
  pollLive();
  if (btn) { btn.disabled = false; btn.textContent = "Send"; }
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
  if (sub) sub.textContent = c.my_name || c.company_name || "Founder OS";
  document.title = c.my_name ? `Founder OS — ${c.my_name}` : "Founder OS";
}

async function refresh() {
  const prevWorld = state.activeWorldId;
  state = { ...state, ...(await api("/state")) };
  state.activeWorldId = prevWorld || state.activeWorldId || "root";
  populateWorldSelect();
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

$("#world-select")?.addEventListener("change", e => {
  setActiveWorld(e.target.value);
  if (currentView === "world" || currentView === "chat" || currentView === "agents") render();
});

FOSMotion?.init?.();
FOSMotion?.runShell?.();

refresh().then(async () => {
  state._agents = await api("/agents").catch(() => ({}));
  state._world = await api("/world").catch(() => ({}));
  populateWorldSelect();
  await loadGraphData();
  render();
  startLivePoll();
});
setInterval(() => refresh().then(() => {
  updateBadges();
  updateStatus();
}), 30000);
