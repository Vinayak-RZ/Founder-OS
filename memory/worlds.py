"""Hierarchical worlds — one root context plus project/idea sub-worlds.

The root world holds generalized founder context and an index of child worlds.
Each child world carries focused context for a startup, research track, or idea.
The agent receives the selected world's context block on every turn.
"""
import json
import re
import uuid
from datetime import datetime
from typing import Optional

from config import config
from memory.sql_store import get_conn

ROOT_ID = "root"
_defaults_seeded = False


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s[:48] or f"world-{uuid.uuid4().hex[:8]}"


def init_worlds_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS worlds (
            id TEXT PRIMARY KEY,
            parent_id TEXT,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            kind TEXT DEFAULT 'project',
            description TEXT DEFAULT '',
            context TEXT DEFAULT '',
            color TEXT DEFAULT '',
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    conn.close()


def ensure_defaults() -> None:
    """Create root world and seed a default child from company config if empty."""
    global _defaults_seeded
    if _defaults_seeded:
        return
    init_worlds_db()
    conn = get_conn()
    root = conn.execute("SELECT id FROM worlds WHERE id = ?", (ROOT_ID,)).fetchone()
    if not root:
        founder = config.my_name or "Founder"
        company = config.company_name or "My Company"
        root_ctx = (
            f"{founder}'s top-level operating context. "
            f"Primary company: {company}. "
            f"{config.my_one_liner or ''}".strip()
        )
        conn.execute(
            """INSERT INTO worlds (id, parent_id, name, slug, kind, description, context, sort_order)
               VALUES (?, NULL, ?, ?, 'root', ?, ?, 0)""",
            (
                ROOT_ID,
                "Main world",
                "main",
                f"Global context across all ventures and ideas for {founder}.",
                root_ctx,
            ),
        )
        conn.commit()

    children = conn.execute(
        "SELECT COUNT(*) AS n FROM worlds WHERE parent_id = ?", (ROOT_ID,)
    ).fetchone()
    if children and children["n"] == 0 and config.company_name:
        slug = _slugify(config.company_name)
        conn.execute(
            """INSERT OR IGNORE INTO worlds
               (id, parent_id, name, slug, kind, description, context, sort_order)
               VALUES (?, ?, ?, ?, 'project', ?, ?, 1)""",
            (
                slug,
                ROOT_ID,
                config.company_name,
                slug,
                f"Primary operating world for {config.company_name}.",
                f"Role: {config.my_role or 'Founder'}. Focus: {config.my_one_liner or 'building the company.'}",
            ),
        )
        conn.commit()
    conn.close()
    _defaults_seeded = True


def _row_to_dict(row) -> dict:
    if not row:
        return {}
    d = dict(row)
    for k in ("created_at", "updated_at"):
        if d.get(k):
            d[k] = str(d[k])
    return d


def get(world_id: str) -> Optional[dict]:
    if not world_id:
        return None
    ensure_defaults()
    conn = get_conn()
    row = conn.execute("SELECT * FROM worlds WHERE id = ?", (world_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def get_tree() -> dict:
    ensure_defaults()
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM worlds ORDER BY parent_id IS NOT NULL, sort_order, name"
    ).fetchall()
    conn.close()
    by_id = {r["id"]: _row_to_dict(r) for r in rows}
    root = by_id.get(ROOT_ID)
    if not root:
        return {"root": None, "children": []}
    children = [w for w in by_id.values() if w.get("parent_id") == ROOT_ID]
    return {"root": root, "children": children}


def list_children() -> list:
    return get_tree().get("children") or []


def create_world(
    name: str,
    kind: str = "project",
    description: str = "",
    context: str = "",
    parent_id: str = ROOT_ID,
) -> dict:
    ensure_defaults()
    name = (name or "").strip()
    if not name:
        raise ValueError("name is required")
    kind = (kind or "project").strip().lower()
    if kind == "root":
        raise ValueError("cannot create another root world")
    parent_id = parent_id or ROOT_ID
    slug = _slugify(name)
    wid = slug
    conn = get_conn()
    existing = conn.execute("SELECT id FROM worlds WHERE id = ? OR slug = ?", (wid, slug)).fetchone()
    if existing:
        wid = f"{slug}-{uuid.uuid4().hex[:6]}"
    n = conn.execute("SELECT COUNT(*) AS c FROM worlds WHERE parent_id = ?", (parent_id,)).fetchone()
    sort_order = (n["c"] or 0) + 1
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO worlds (id, parent_id, name, slug, kind, description, context, sort_order, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (wid, parent_id, name, slug, kind, description or "", context or "", sort_order, now),
    )
    conn.commit()
    conn.close()
    return get(wid)


def update_world(world_id: str, **fields) -> Optional[dict]:
    if world_id == ROOT_ID:
        allowed = {"description", "context", "name"}
    else:
        allowed = {"name", "kind", "description", "context", "color", "sort_order"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get(world_id)
    updates["updated_at"] = datetime.now().isoformat(timespec="seconds")
    sets = ", ".join(f"{k} = ?" for k in updates)
    conn = get_conn()
    conn.execute(f"UPDATE worlds SET {sets} WHERE id = ?", (*updates.values(), world_id))
    conn.commit()
    conn.close()
    return get(world_id)


def delete_world(world_id: str) -> bool:
    if world_id in (ROOT_ID, "main", None, ""):
        raise ValueError("cannot delete the root world")
    conn = get_conn()
    cur = conn.execute("DELETE FROM worlds WHERE id = ? AND parent_id IS NOT NULL", (world_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def resolve_world_id(world_id: Optional[str]) -> Optional[str]:
    """Normalize client world selection. None/'global'/'root' → root context."""
    if not world_id or world_id in ("global", "root", "main", ""):
        return ROOT_ID
    w = get(world_id)
    return w["id"] if w else ROOT_ID


def snapshot_block(world_id: Optional[str] = None, max_chars: int = 2200) -> str:
    """Text injected into the agent system prompt for the active world."""
    from memory import world_model

    ensure_defaults()
    wid = resolve_world_id(world_id)
    tree = get_tree()
    root = tree.get("root") or {}
    children = tree.get("children") or []

    try:
        global_snap = world_model.build_snapshot()
    except Exception:
        global_snap = {}

    lines = []

    if wid == ROOT_ID:
        lines.append(f"[WORLD: {root.get('name', 'Main world')} — top level]")
        if root.get("description"):
            lines.append(root["description"])
        if root.get("context"):
            lines.append("Context:\n" + (root["context"] or "")[:800])
        if children:
            lines.append("\nSub-worlds (delegate or switch context for detail):")
            for c in children[:12]:
                lines.append(
                    f"  • {c['name']} ({c.get('kind', 'project')}, id={c['id']}): "
                    f"{(c.get('description') or '')[:120]}"
                )
        lines.append("\n" + _format_global_snap(global_snap))
    else:
        child = get(wid) or {}
        lines.append(f"[WORLD: {child.get('name', wid)} — focused context]")
        lines.append(f"Parent: {root.get('name', 'Main world')} (id={ROOT_ID})")
        if child.get("description"):
            lines.append(child["description"])
        if child.get("context"):
            lines.append("Focused context:\n" + (child["context"] or "")[:1200])
        lines.append("\nGlobal awareness (abbreviated):")
        lines.append(_format_global_snap(global_snap, brief=True))

    text = "\n".join(lines)
    return text[:max_chars]


def _format_global_snap(snap: dict, brief: bool = False) -> str:
    if not snap:
        return "Global snapshot unavailable."
    crm = snap.get("crm") or {}
    parts = [
        f"CRM: {crm.get('total_contacts', 0)} contacts, {crm.get('followups_due', 0)} follow-ups",
        f"Tasks: {snap.get('tasks_open', 0)} | Approvals: {snap.get('approvals_pending', 0)}",
    ]
    if not brief and snap.get("goals_active"):
        parts.append("Goals: " + "; ".join(snap["goals_active"][:4]))
    fin = snap.get("finance") or {}
    if fin.get("set") and fin.get("runway_months") is not None:
        parts.append(f"Runway: ~{fin['runway_months']} mo [{fin.get('status', '')}]")
    return " | ".join(parts)


def hierarchy_for_graph() -> dict:
    """Nodes/edges for UI hierarchy visualization."""
    tree = get_tree()
    root = tree.get("root")
    children = tree.get("children") or []
    nodes = []
    edges = []
    if root:
        nodes.append({"id": root["id"], "label": root["name"], "type": "world_root"})
        for c in children:
            nodes.append({
                "id": c["id"],
                "label": c["name"],
                "type": "world_child",
                "kind": c.get("kind", "project"),
            })
            edges.append({"source": root["id"], "target": c["id"], "label": c.get("kind", "")})
    return {"nodes": nodes, "edges": edges}


init_worlds_db()
