"""Founder World Model — a live snapshot of the founder's business state.

Aggregates CRM pipeline, goals, projects, follow-ups, reminders, pending approvals,
strategy experiments, and budget into one structured view the agent can reason over.
Refreshed on every turn (cheap — all local DB reads) and persisted to disk so
heartbeats and debugging can inspect the same picture.

This is the agent's "situational awareness": it always knows what's going on
without the founder having to re-explain context every message.
"""
import json
import os
from datetime import datetime

from agent import store, budget, finance
from memory.sql_store import get_all_contacts, get_contacts_needing_followup, get_pending_tasks

STATE_PATH = "./data/world_state/latest.json"


def build_snapshot() -> dict:
    contacts = get_all_contacts()
    by_status = {}
    for c in contacts:
        st = c.get("status") or "unknown"
        by_status[st] = by_status.get(st, 0) + 1

    followups = get_contacts_needing_followup()
    tasks = get_pending_tasks()

    goals = store.list_goals("active")
    reminders = store.get_pending_reminders()
    approvals = store.list_pending_approvals()
    projects = []
    for p in store.list_open_plans():
        if (p.get("rationale") or "") != "durable project":
            continue
        full = store.get_plan(p["id"]) or {}
        subs = full.get("subtasks", [])
        done = sum(1 for s in subs if s.get("status") == "done")
        projects.append({"id": p["id"], "goal": p["goal"], "progress": f"{done}/{len(subs)}"})

    strategies = store.all_strategies(6)
    usage = budget.status()

    snap = {
        "ts": datetime.now().isoformat(timespec="minutes"),
        "crm": {"total_contacts": len(contacts), "by_status": by_status,
                "followups_due": len(followups)},
        "tasks_open": len(tasks),
        "goals_active": [g["title"] for g in goals[:8]],
        "reminders_pending": len(reminders),
        "approvals_pending": len(approvals),
        "projects_open": projects,
        "top_strategies": [
            {"group": s["grp"], "variant": s["variant"],
             "rate": round(s.get("successes", 0) / max(s.get("trials", 1), 1), 2)}
            for s in strategies
        ],
        "finance": finance.summary(),
        "usage_today": usage,
    }

    try:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(snap, f, indent=2, default=str)
    except Exception:
        pass
    return snap


def snapshot_block(max_chars: int = 1200) -> str:
    """Compact text block for system-prompt injection."""
    s = build_snapshot()
    lines = [
        f"Snapshot @ {s['ts']}",
        f"CRM: {s['crm']['total_contacts']} contacts ({s['crm']['by_status']}), "
        f"{s['crm']['followups_due']} follow-ups due",
        f"Open tasks: {s['tasks_open']} | Pending reminders: {s['reminders_pending']} | "
        f"Pending approvals: {s['approvals_pending']}",
    ]
    if s["goals_active"]:
        lines.append("Active goals: " + "; ".join(s["goals_active"][:5]))
    if s["projects_open"]:
        lines.append("Open projects: " + ", ".join(
            f"#{p['id']} {p['goal'][:40]} ({p['progress']})" for p in s["projects_open"][:3]))
    if s["approvals_pending"]:
        lines.append(f"⚠ {s['approvals_pending']} action(s) waiting for your approval.")
    fin = s.get("finance") or {}
    if fin.get("set"):
        if fin.get("runway_months") is not None:
            lines.append(f"Runway: ~{fin['runway_months']} months "
                         f"(cash ${fin.get('cash', 0):,.0f}, net burn ${fin.get('net_burn', 0):,.0f}/mo) "
                         f"[{fin.get('status')}]")
        else:
            lines.append(f"Finance: {fin.get('runway', 'cash-flow positive')} "
                         f"(cash ${fin.get('cash', 0):,.0f})")
        warn = finance.warning_line()
        if warn:
            lines.append(warn)
    u = s.get("usage_today") or {}
    lines.append(f"Today: {u.get('llm_calls', 0)} LLM calls, est ${u.get('est_cost_usd', 0)}")
    text = "\n".join(lines)
    return text[:max_chars]
