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
    from memory import worlds as hierarchical_worlds
    import agent.trace as trace
    from dashboard import notifications

    return {
        "about": _safe(about.describe, {}),
        "worlds": _safe(hierarchical_worlds.get_tree, {}),
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
        "integrations": {
            "gmail": bool(config.gmail_address and config.gmail_app_password),
            "calendar": os.path.isfile(config.google_token_path),
            "qdrant": bool(config.qdrant_url),
            "x": bool(config.x_bearer_token or config.x_api_key),
            "serper": bool(config.serper_api_key),
            "tavily": bool(config.tavily_api_key),
        },
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

    from dashboard import live_ops

    async def _on_status(text: str):
        live_ops.set_phase(text)

    world_id = (data.get("world_id") or "").strip() or None

    async def _go():
        live_ops.begin("user", message)
        try:
            return await core.run(message, actor="user", on_status=_on_status, world_id=world_id)
        finally:
            live_ops.end()

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
        "traces_full": _safe(lambda: trace.recent_full(15), []),
        "actions": _safe(lambda: store.recent_actions(30), []),
        "usage_history": _safe(lambda: store.usage_history(14), []),
    })


@bp.route("/live")
def api_live():
    from dashboard import live_ops
    return jsonify(live_ops.snapshot())


@bp.route("/agents")
def api_agents():
    from agent import subagent, registry
    from agent import skills_catalog
    specs = []
    for name in subagent.list_specialists():
        meta = subagent.specialist_meta(name)
        spec = subagent.SPECIALISTS[name]
        cats = spec["categories"]
        tools = [t for t in registry.all_tools() if t.category in cats]
        specs.append({
            **meta,
            "tool_count": len(tools),
        })
    live = _safe(lambda: __import__("dashboard.live_ops", fromlist=["snapshot"]).snapshot(), {})
    return jsonify({
        "supervisor": {
            "id": "supervisor",
            "label": "Supervisor",
            "role": "Aggregator — routes tasks, tracks parallel projects, orchestrates specialists",
            "status": "busy" if live.get("active") else "ready",
        },
        "specialists": specs,
        "skills": _safe(skills_catalog.list_skills, []),
        "mission": "aggregator",
        "total_tools": len(registry.all_tools()),
        "live": live,
    })


@bp.route("/agents/runs")
def api_agent_runs():
    import agent.trace as trace
    from agent import store
    runs = []
    for t in _safe(lambda: trace.recent_full(40), []):
        actor = t.get("actor") or ""
        if not actor.startswith("subagent:"):
            continue
        runs.append({
            "id": t.get("id"),
            "agent": actor.split(":", 1)[-1],
            "task": t.get("message", ""),
            "result": t.get("final", ""),
            "duration_s": t.get("duration_s", 0),
            "ts": t.get("ts"),
            "tools": [e.get("name") for e in t.get("events", []) if e.get("name")],
        })
    return jsonify({
        "runs": runs,
        "actions": _safe(lambda: store.recent_actions(25), []),
    })


@bp.route("/agents/delegate", methods=["POST"])
def api_delegate():
    data = request.get_json(silent=True) or {}
    specialist = (data.get("specialist") or "").strip()
    task = (data.get("task") or "").strip()
    world_id = (data.get("world_id") or "").strip() or None
    if not specialist or not task:
        return jsonify({"error": "specialist and task are required"}), 400
    from agent import subagent
    from dashboard import live_ops

    async def _on_status(text: str):
        live_ops.set_phase(text)

    async def _go():
        live_ops.begin(f"subagent:{specialist}", task)
        try:
            return await subagent.run_subagent(
                specialist, task, actor="user", on_status=_on_status, world_id=world_id,
            )
        finally:
            live_ops.end()

    try:
        result = _run_async(_go())
    except Exception as e:
        logger.exception("delegate failed")
        return jsonify({"error": str(e)[:500]}), 500
    return jsonify(result)


@bp.route("/world")
def api_world():
    from memory import world_model
    from agent import about, registry, store
    from collections import Counter
    from dashboard import graph_viz
    from memory import worlds as hierarchical_worlds
    snap = _safe(world_model.build_snapshot, {})
    tree = _safe(hierarchical_worlds.get_tree, {})
    cats = Counter(t.category for t in registry.all_tools())
    graph = _safe(
        lambda: graph_viz.build_world_graph(snap, store.list_goals("active"), tree),
        {},
    )
    return jsonify({
        "snapshot": snap,
        "worlds": tree,
        "tools_by_category": dict(sorted(cats.items(), key=lambda kv: -kv[1])),
        "total_tools": len(registry.all_tools()),
        "about": _safe(about.describe, {}),
        "graph": graph,
    })


@bp.route("/graph/runtime")
def api_graph_runtime():
    from agent import subagent
    from dashboard import graph_viz, live_ops
    live = live_ops.snapshot()
    specs = subagent.list_specialists()
    return jsonify(graph_viz.build_runtime_graph(live, specs))


@bp.route("/graph/world")
def api_graph_world():
    from memory import world_model
    from agent import store
    from dashboard import graph_viz
    from memory import worlds as hierarchical_worlds
    snap = _safe(world_model.build_snapshot, {})
    goals = _safe(lambda: store.list_goals("active"), [])
    tree = _safe(hierarchical_worlds.get_tree, {})
    previews = {}
    root = tree.get("root")
    if root:
        previews[root["id"]] = _safe(
            lambda: hierarchical_worlds.snapshot_block(root["id"], max_chars=1600), ""
        )
    for child in tree.get("children") or []:
        cid = child.get("id")
        if cid:
            previews[cid] = _safe(
                lambda c=cid: hierarchical_worlds.snapshot_block(c, max_chars=1600), ""
            )
    return jsonify({
        "snapshot": snap,
        "worlds": tree,
        "graph": graph_viz.build_world_graph(snap, goals, tree),
        "hierarchy_graph": graph_viz.build_world_hierarchy_graph(tree),
        "world_previews": previews,
    })


@bp.route("/graph/memory")
def api_graph_memory():
    from memory import graph as kg
    from memory.vector_store import collections_overview
    from dashboard import graph_viz
    kg_data = _safe(lambda: kg.export_graph(), {"entities": [], "relations": []})
    cols = _safe(lambda: collections_overview(samples_per=4), [])
    return jsonify({
        "knowledge_graph": kg_data,
        "collections": cols,
        "graph": graph_viz.build_memory_graph(kg_data, cols),
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
    world_id = (request.form.get("world_id") or "").strip() or None
    reply = _run_async(core.run(message, actor="user", world_id=world_id))
    return jsonify({"reply": reply, "filename": f.filename})


@bp.route("/worlds")
def api_worlds_list():
    from memory import worlds as hierarchical_worlds
    return jsonify(hierarchical_worlds.get_tree())


@bp.route("/worlds", methods=["POST"])
def api_worlds_create():
    from memory import worlds as hierarchical_worlds
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    try:
        w = hierarchical_worlds.create_world(
            name=name,
            kind=(data.get("kind") or "project").strip(),
            description=(data.get("description") or "").strip(),
            context=(data.get("context") or "").strip(),
            template=(data.get("template") or "").strip() or None,
            github_repo=(data.get("github_repo") or "").strip(),
            repo_path=(data.get("repo_path") or "").strip(),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"world": w, "tree": hierarchical_worlds.get_tree()})


@bp.route("/worlds/<world_id>", methods=["PATCH"])
def api_worlds_update(world_id):
    from memory import worlds as hierarchical_worlds
    data = request.get_json(silent=True) or {}
    w = _safe(lambda: hierarchical_worlds.update_world(world_id, **data), None)
    if not w:
        return jsonify({"error": "world not found"}), 404
    return jsonify({"world": w, "tree": hierarchical_worlds.get_tree()})


@bp.route("/worlds/<world_id>", methods=["DELETE"])
def api_worlds_delete(world_id):
    from memory import worlds as hierarchical_worlds
    try:
        ok = hierarchical_worlds.delete_world(world_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if not ok:
        return jsonify({"error": "world not found"}), 404
    return jsonify({"ok": True, "tree": hierarchical_worlds.get_tree()})


@bp.route("/world-templates")
def api_world_templates():
    from memory import world_templates
    return jsonify({"templates": world_templates.list_templates()})


@bp.route("/worlds/<world_id>/vault")
def api_world_vault(world_id):
    from memory import worlds as hierarchical_worlds
    from memory import knowledge_vault
    from memory.world_templates import template_for_kind
    w = hierarchical_worlds.get(world_id)
    if not w:
        return jsonify({"error": "world not found"}), 404
    tpl = w.get("template") or template_for_kind(w.get("kind", "project"))
    structure = _safe(
        lambda: knowledge_vault.vault_structure(world_id, w.get("slug") or world_id, tpl),
        {},
    )
    return jsonify({"world": w, "vault": structure})


@bp.route("/worlds/<world_id>/vault/ingest", methods=["POST"])
def api_world_vault_ingest(world_id):
    from memory import worlds as hierarchical_worlds
    from memory import knowledge_vault
    from memory.world_templates import template_for_kind
    data = request.get_json(silent=True) or {}
    w = hierarchical_worlds.get(world_id)
    if not w:
        return jsonify({"error": "world not found"}), 404
    tpl = w.get("template") or template_for_kind(w.get("kind", "project"))
    slug = w.get("slug") or world_id
    path = (data.get("path") or "").strip()
    if not path:
        path = str(knowledge_vault.world_vault_path(world_id, slug))
    result = _safe(lambda: knowledge_vault.ingest_tree(path, world_id, slug, tpl), {"error": "ingest failed"})
    return jsonify(result)


@bp.route("/worlds/<world_id>/vault/link-repo", methods=["POST"])
def api_world_vault_link_repo(world_id):
    from memory import worlds as hierarchical_worlds
    from memory import knowledge_vault
    from memory.world_templates import template_for_kind
    data = request.get_json(silent=True) or {}
    repo_path = (data.get("repo_path") or "").strip()
    if not repo_path:
        return jsonify({"error": "repo_path is required"}), 400
    w = hierarchical_worlds.get(world_id)
    if not w:
        return jsonify({"error": "world not found"}), 404
    tpl = w.get("template") or template_for_kind(w.get("kind", "project"))
    slug = w.get("slug") or world_id
    hierarchical_worlds.update_world(world_id, repo_path=repo_path)
    result = _safe(lambda: knowledge_vault.link_repo(world_id, slug, repo_path, tpl), {"error": "link failed"})
    return jsonify(result)


@bp.route("/vault/search")
def api_vault_search():
    from memory import knowledge_vault
    q = (request.args.get("q") or "").strip()
    world_id = (request.args.get("world_id") or "").strip() or None
    domain = (request.args.get("domain") or "").strip() or None
    if not q:
        return jsonify({"error": "q is required"}), 400
    hits = _safe(lambda: knowledge_vault.search_vault(q, world_id=world_id, domain=domain), [])
    return jsonify({"query": q, "hits": hits})
