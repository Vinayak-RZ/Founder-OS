"""JSON API for the Founder OS web UI."""
import asyncio
import json
import logging
import os

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)
bp = Blueprint("api", __name__, url_prefix="/api")


def _safe(fn, default=None):
    try:
        return fn()
    except Exception as e:
        logger.debug(f"[api] {fn.__name__ if hasattr(fn, '__name__') else fn} failed: {e}")
        return default


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def collect_state() -> dict:
    from agent import about, budget, finance, store
    from memory import world_model
    import agent.trace as trace
    from dashboard import notifications

    return {
        "about": _safe(about.describe, {}),
        "snapshot": _safe(world_model.build_snapshot, {}),
        "usage": _safe(budget.status, {}),
        "finance": _safe(finance.summary, {}),
        "approvals": _safe(store.list_pending_approvals, []),
        "goals": _safe(lambda: store.list_goals("active"), []),
        "reminders": _safe(store.get_pending_reminders, []),
        "tasks": _safe(lambda: __import__("memory.sql_store", fromlist=["get_pending_tasks"]).get_pending_tasks(), []),
        "traces": _safe(lambda: trace.recent(15), []),
        "actions": _safe(lambda: store.recent_actions(20), []),
        "usage_history": _safe(lambda: store.usage_history(7), []),
        "notifications": _safe(notifications.list_items, []),
        "unread_notifications": _safe(notifications.unread_count, 0),
        "config": _safe(_public_config, {}),
    }


def _public_config():
    from config import config
    return {
        "my_name": config.my_name,
        "company_name": config.company_name,
        "autonomy_level": config.autonomy_level,
        "agent_paused": config.agent_paused,
        "auto_approve": config.auto_approve,
        "telegram_enabled": config.telegram_enabled,
        "web_ui_enabled": config.web_ui_enabled,
        "dashboard_port": config.dashboard_port,
    }


@bp.route("/state")
def api_state():
    return jsonify(collect_state())


@bp.route("/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    from agent import core, store

    before = {a["id"] for a in store.list_pending_approvals()}

    async def _go():
        return await core.run(message, actor="user")

    try:
        reply = _run_async(_go())
    except Exception as e:
        logger.exception("chat failed")
        return jsonify({"error": str(e)[:500]}), 500

    new_approvals = [a for a in store.list_pending_approvals() if a["id"] not in before]
    return jsonify({
        "reply": reply,
        "new_approvals": new_approvals,
        "pending_approvals": store.list_pending_approvals(),
    })


@bp.route("/approvals")
def api_approvals():
    from agent import store
    return jsonify({"approvals": store.list_pending_approvals()})


@bp.route("/approvals/<int:aid>/approve", methods=["POST"])
def api_approve(aid):
    from agent import approvals
    reply = _run_async(approvals.approve(aid))
    return jsonify({"result": reply})


@bp.route("/approvals/<int:aid>/reject", methods=["POST"])
def api_reject(aid):
    from agent import approvals
    reply = _run_async(approvals.reject(aid))
    return jsonify({"result": reply})


@bp.route("/crm/contacts")
def api_contacts():
    from memory.sql_store import get_all_contacts, get_pipeline_summary, get_contacts_needing_followup
    return jsonify({
        "contacts": _safe(get_all_contacts, []),
        "pipeline": _safe(get_pipeline_summary, {}),
        "followups_due": _safe(get_contacts_needing_followup, []),
    })


@bp.route("/goals")
def api_goals():
    from agent import store
    return jsonify({
        "active": _safe(lambda: store.list_goals("active"), []),
        "done": _safe(lambda: store.list_goals("done"), []),
        "plans": _safe(store.list_open_plans, []),
        "reminders": _safe(store.get_pending_reminders, []),
        "skills": _safe(store.list_skills, []),
        "lessons": _safe(lambda: store.recent_lessons(15), []),
    })


@bp.route("/memory/search")
def api_memory_search():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"results": []})
    from memory.vector_store import search_all
    return jsonify({"results": _safe(lambda: search_all(q, n_results=8), [])})


@bp.route("/tools")
def api_tools():
    from agent import registry
    from collections import Counter
    tools = registry.all_tools()
    by_cat = Counter(t.category for t in tools)
    return jsonify({
        "total": len(tools),
        "by_category": dict(by_cat),
        "tools": [{
            "name": t.name,
            "description": t.description,
            "category": t.category,
            "requires_approval": t.requires_approval,
        } for t in sorted(tools, key=lambda x: (x.category, x.name))],
    })


@bp.route("/activity")
def api_activity():
    import agent.trace as trace
    from agent import store
    return jsonify({
        "traces": _safe(lambda: trace.recent(25), []),
        "actions": _safe(lambda: store.recent_actions(30), []),
        "usage_history": _safe(lambda: store.usage_history(14), []),
    })


@bp.route("/notifications")
def api_notifications():
    from dashboard import notifications
    unread = request.args.get("unread") == "1"
    return jsonify({
        "items": notifications.list_items(50, unread_only=unread),
        "unread": notifications.unread_count(),
    })


@bp.route("/notifications/<item_id>/read", methods=["POST"])
def api_notification_read(item_id):
    from dashboard import notifications
    notifications.mark_read(item_id)
    return jsonify({"ok": True, "unread": notifications.unread_count()})


@bp.route("/notifications/read-all", methods=["POST"])
def api_notifications_read_all():
    from dashboard import notifications
    notifications.mark_all_read()
    return jsonify({"ok": True})


@bp.route("/agent/pause", methods=["POST"])
def api_agent_pause():
    """Toggle kill switch via env override in-process (session only)."""
    import os
    from config import config
    data = request.get_json(silent=True) or {}
    paused = bool(data.get("paused"))
    os.environ["AGENT_PAUSED"] = "true" if paused else "false"
    config.agent_paused = paused
    return jsonify({"agent_paused": paused})


@bp.route("/upload", methods=["POST"])
def api_upload():
    """Upload a document for the agent to read."""
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    caption = (request.form.get("caption") or "").strip()
    raw = f.read()
    from integrations import documents
    extracted = documents.extract_text(raw, filename=f.filename or "upload")
    message = f"The founder uploaded '{f.filename}'. Notes: {caption or '(none)'}."
    if extracted:
        message += f"\n\n[DOCUMENT CONTENT]\n{extracted[:50000]}"
    from agent import core
    reply = _run_async(core.run(message, actor="user"))
    return jsonify({"reply": reply, "filename": f.filename})
