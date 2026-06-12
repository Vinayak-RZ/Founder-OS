/** Inline SVG icons for sidebar nav (loaded before app.js). */
window.FOS_NAV_ICONS = {
  dashboard: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="5" rx="1.5"/><rect x="13" y="10" width="8" height="11" rx="1.5"/><rect x="3" y="13" width="8" height="8" rx="1.5"/></svg>',
  chat: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 11.5a8.4 8.4 0 0 1-1.1 4.2 8.5 8.5 0 0 1-7.4 4.3 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.3-7.4 8.4 8.4 0 0 1 4.2-1.1h.4a8.5 8.5 0 0 1 8.1 8.1z"/></svg>',
  agents: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="9" cy="8" r="3.5"/><circle cx="17" cy="9" r="2.5"/><path d="M3 19v-.5A4.5 4.5 0 0 1 7.5 14H10a4.5 4.5 0 0 1 4.5 4.5V19"/><path d="M15 14h.5A3.5 3.5 0 0 1 19 17.5V19"/></svg>',
  world: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 4 9 15 15 0 0 1-4 9 15 15 0 0 1-4-9 15 15 0 0 1 4-9z"/></svg>',
  approvals: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 11l2 2 4-4"/><rect x="4" y="4" width="16" height="16" rx="2"/></svg>',
  crm: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 10h16M4 14h10M4 18h7"/><circle cx="18" cy="16" r="3"/></svg>',
  goals: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none"/></svg>',
  memory: '<svg viewBox="0 0 24 24" aria-hidden="true"><ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6"/><path d="M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/></svg>',
  tools: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L4 17l3 3 6.3-5.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.1-2.1 2.5-2.5z"/></svg>',
  history: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 8v5l3 2"/><circle cx="12" cy="12" r="9"/><path d="M5 3 2 6"/><path d="M22 6l-3-3"/></svg>',
  activity: '<svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="4 16 8 12 12 14 16 8 20 10"/><path d="M4 20h16"/></svg>',
  settings: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
  more: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5" cy="12" r="1.75" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.75" fill="currentColor" stroke="none"/><circle cx="19" cy="12" r="1.75" fill="currentColor" stroke="none"/></svg>',
};

const MOBILE_PRIMARY_VIEWS = new Set(["dashboard", "chat", "agents", "world"]);

function iconHtml(key) {
  return window.FOS_NAV_ICONS?.[key] || "";
}

function decorateNavIcons() {
  document.querySelectorAll(".nav-link[data-view]").forEach(btn => {
    const key = btn.dataset.view;
    const svg = iconHtml(key);
    if (!svg) return;
    const body = btn.querySelector(".nav-link__body");
    if (!body || body.querySelector(".nav-icon")) return;
    const icon = document.createElement("span");
    icon.className = "nav-icon";
    icon.innerHTML = svg;
    body.prepend(icon);
  });

  document.querySelectorAll("[data-icon]").forEach(el => {
    const svg = iconHtml(el.dataset.icon);
    if (svg) el.innerHTML = svg;
  });
}

window.FOS_MOBILE_PRIMARY_VIEWS = MOBILE_PRIMARY_VIEWS;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", decorateNavIcons);
} else {
  decorateNavIcons();
}
