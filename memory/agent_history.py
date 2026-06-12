"""Persistent agent history — sessions, messages, runs, and artifacts.

Stores structured metadata in SQLite (same DB as CRM/goals). File payloads stay on
disk under data/documents/ or S3 via vault; this module records links and lineage.
"""
from __future__ import annotations

import contextvars
import json
import os
import uuid
from datetime import datetime
from typing import Optional

from memory.sql_store import get_conn

_ctx_session = contextvars.ContextVar("agent_history_session", default=None)
_ctx_world = contextvars.ContextVar("agent_history_world", default=None)
_ctx_specialist = contextvars.ContextVar("agent_history_specialist", default="supervisor")
_ctx_run = contextvars.ContextVar("agent_history_run", default=None)

DOCS_DIR = os.path.abspath("./data/documents")


def init_agent_history_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS agent_sessions (
            id TEXT PRIMARY KEY,
            world_id TEXT,
            specialist TEXT DEFAULT 'supervisor',
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS agent_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            run_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS agent_runs (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            trace_id TEXT,
            actor TEXT,
            specialist TEXT,
            world_id TEXT,
            user_message TEXT,
            assistant_reply TEXT,
            tools_json TEXT,
            duration_s REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS agent_artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            session_id TEXT,
            world_id TEXT,
            kind TEXT NOT NULL,
            title TEXT,
            path TEXT,
            storage_key TEXT,
            mime_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_agent_messages_session
            ON agent_messages(session_id, id);
        CREATE INDEX IF NOT EXISTS idx_agent_runs_session
            ON agent_runs(session_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_agent_artifacts_run
            ON agent_artifacts(run_id);
        CREATE INDEX IF NOT EXISTS idx_agent_artifacts_created
            ON agent_artifacts(created_at DESC);
        """
    )
    conn.close()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def begin_turn(
    *,
    session_id: str | None = None,
    world_id: str | None = None,
    specialist: str = "supervisor",
    title: str | None = None,
) -> str:
    """Open a turn context; create a session when none is supplied."""
    sid = (session_id or "").strip() or None
    spec = (specialist or "supervisor").strip() or "supervisor"
    wid = (world_id or "").strip() or None
    if sid and not get_session(sid):
        sid = None
    if not sid:
        sid = create_session(world_id=wid, specialist=spec, title=title)
    _ctx_session.set(sid)
    _ctx_world.set(wid)
    _ctx_specialist.set(spec)
    _ctx_run.set(None)
    return sid


def end_turn():
    _ctx_session.set(None)
    _ctx_world.set(None)
    _ctx_specialist.set("supervisor")
    _ctx_run.set(None)


def current_session_id() -> str | None:
    return _ctx_session.get()


def current_run_id() -> str | None:
    return _ctx_run.get()


def create_session(
    *,
    world_id: str | None = None,
    specialist: str = "supervisor",
    title: str | None = None,
) -> str:
    init_agent_history_db()
    sid = _new_id()
    now = _now()
    conn = get_conn()
    conn.execute(
        """INSERT INTO agent_sessions (id, world_id, specialist, title, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (sid, world_id, specialist or "supervisor", (title or "New conversation")[:200], now, now),
    )
    conn.commit()
    conn.close()
    return sid


def touch_session(session_id: str):
    conn = get_conn()
    conn.execute(
        "UPDATE agent_sessions SET updated_at = ? WHERE id = ?",
        (_now(), session_id),
    )
    conn.commit()
    conn.close()


def get_session(session_id: str) -> dict | None:
    init_agent_history_db()
    conn = get_conn()
    row = conn.execute("SELECT * FROM agent_sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_message(
    session_id: str,
    role: str,
    content: str,
    *,
    run_id: str | None = None,
) -> int:
    init_agent_history_db()
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO agent_messages (session_id, role, content, run_id, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (session_id, role, content, run_id, _now()),
    )
    msg_id = cur.lastrowid
    conn.commit()
    conn.close()
    touch_session(session_id)
    return msg_id


def persist_run_from_trace(trace_record: dict) -> str | None:
    """Persist a finished trace as an agent_run; uses turn context when set."""
    if not trace_record:
        return None
    init_agent_history_db()
    session_id = _ctx_session.get()
    run_id = trace_record.get("id") or _new_id()
    tools = [
        {
            "name": e.get("data", {}).get("name"),
            "decision": e.get("data", {}).get("decision"),
            "t": e.get("t"),
        }
        for e in trace_record.get("events", [])
        if e.get("type") == "tool"
    ]
    actor = trace_record.get("actor") or "user"
    specialist = _ctx_specialist.get() or "supervisor"
    if actor.startswith("subagent:"):
        specialist = actor.split(":", 1)[-1]
    world_id = _ctx_world.get()
    now = _now()
    conn = get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO agent_runs
           (id, session_id, trace_id, actor, specialist, world_id,
            user_message, assistant_reply, tools_json, duration_s, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run_id,
            session_id,
            run_id,
            actor,
            specialist,
            world_id,
            (trace_record.get("message") or "")[:4000],
            (trace_record.get("final") or "")[:8000],
            json.dumps(tools, default=str),
            trace_record.get("duration_s") or 0,
            now,
        ),
    )
    conn.commit()
    conn.close()
    _ctx_run.set(run_id)
    if session_id:
        touch_session(session_id)
    return run_id


def register_artifact(
    *,
    kind: str,
    title: str,
    path: str | None = None,
    storage_key: str | None = None,
    mime_type: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    world_id: str | None = None,
) -> dict:
    """Record a file the agent created; optionally notify the dashboard."""
    init_agent_history_db()
    run_id = run_id or _ctx_run.get()
    session_id = session_id or _ctx_session.get()
    world_id = world_id or _ctx_world.get()
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO agent_artifacts
           (run_id, session_id, world_id, kind, title, path, storage_key, mime_type, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run_id,
            session_id,
            world_id,
            kind,
            (title or "Untitled")[:300],
            path,
            storage_key,
            mime_type,
            _now(),
        ),
    )
    artifact_id = cur.lastrowid
    conn.commit()
    conn.close()
    return get_artifact(artifact_id) or {"id": artifact_id}


def get_artifact(artifact_id: int) -> dict | None:
    init_agent_history_db()
    conn = get_conn()
    row = conn.execute("SELECT * FROM agent_artifacts WHERE id = ?", (artifact_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def artifact_file_path(artifact_id: int) -> str | None:
    """Resolve a safe local path for download."""
    art = get_artifact(artifact_id)
    if not art:
        return None
    path = art.get("path")
    if not path:
        return None
    abs_path = os.path.abspath(path)
    docs_root = DOCS_DIR
    if abs_path.startswith(docs_root) and os.path.isfile(abs_path):
        return abs_path
    return None


def read_artifact_text(artifact_id: int) -> str | None:
    path = artifact_file_path(artifact_id)
    if not path:
        return None
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".md", ".txt", ".markdown"):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def write_artifact_text(artifact_id: int, content: str) -> bool:
    path = artifact_file_path(artifact_id)
    if not path:
        return False
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".md", ".txt", ".markdown"):
        return False
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content or "")
        return True
    except OSError:
        return False


def list_sessions(limit: int = 40, world_id: str | None = None) -> list[dict]:
    init_agent_history_db()
    conn = get_conn()
    if world_id:
        rows = conn.execute(
            """SELECT s.*,
                      (SELECT COUNT(*) FROM agent_messages m WHERE m.session_id = s.id) AS message_count,
                      (SELECT COUNT(*) FROM agent_runs r WHERE r.session_id = s.id) AS run_count
               FROM agent_sessions s
               WHERE s.world_id = ?
               ORDER BY s.updated_at DESC LIMIT ?""",
            (world_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT s.*,
                      (SELECT COUNT(*) FROM agent_messages m WHERE m.session_id = s.id) AS message_count,
                      (SELECT COUNT(*) FROM agent_runs r WHERE r.session_id = s.id) AS run_count
               FROM agent_sessions s
               ORDER BY s.updated_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session_detail(session_id: str) -> dict | None:
    sess = get_session(session_id)
    if not sess:
        return None
    conn = get_conn()
    messages = conn.execute(
        """SELECT id, role, content, run_id, created_at
           FROM agent_messages WHERE session_id = ? ORDER BY id ASC""",
        (session_id,),
    ).fetchall()
    runs = conn.execute(
        """SELECT id, actor, specialist, user_message, assistant_reply,
                  tools_json, duration_s, created_at
           FROM agent_runs WHERE session_id = ? ORDER BY created_at ASC""",
        (session_id,),
    ).fetchall()
    artifacts = conn.execute(
        """SELECT id, run_id, kind, title, path, mime_type, created_at
           FROM agent_artifacts WHERE session_id = ? ORDER BY created_at ASC""",
        (session_id,),
    ).fetchall()
    conn.close()
    run_rows = []
    for r in runs:
        row = dict(r)
        try:
            row["tools"] = json.loads(row.pop("tools_json") or "[]")
        except Exception:
            row["tools"] = []
        run_rows.append(row)
    return {
        **sess,
        "messages": [dict(m) for m in messages],
        "runs": run_rows,
        "artifacts": [dict(a) for a in artifacts],
    }


def list_history(limit: int = 40, world_id: str | None = None) -> dict:
    sessions = list_sessions(limit, world_id=world_id)
    recent_runs = list_runs(limit=min(limit, 30), world_id=world_id)
    return {"sessions": sessions, "recent_runs": recent_runs}


def list_runs(limit: int = 30, session_id: str | None = None, world_id: str | None = None) -> list[dict]:
    init_agent_history_db()
    conn = get_conn()
    q = """SELECT id, session_id, actor, specialist, world_id, user_message,
                  substr(assistant_reply, 1, 300) AS assistant_reply,
                  tools_json, duration_s, created_at
           FROM agent_runs"""
    params: list = []
    clauses = []
    if session_id:
        clauses.append("session_id = ?")
        params.append(session_id)
    if world_id:
        clauses.append("world_id = ?")
        params.append(world_id)
    if clauses:
        q += " WHERE " + " AND ".join(clauses)
    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    out = []
    for r in rows:
        row = dict(r)
        try:
            row["tools"] = json.loads(row.pop("tools_json") or "[]")
        except Exception:
            row["tools"] = []
        out.append(row)
    return out


def list_artifacts(
    limit: int = 50,
    session_id: str | None = None,
    run_id: str | None = None,
    world_id: str | None = None,
) -> list[dict]:
    init_agent_history_db()
    conn = get_conn()
    q = "SELECT * FROM agent_artifacts"
    params: list = []
    clauses = []
    if session_id:
        clauses.append("session_id = ?")
        params.append(session_id)
    if run_id:
        clauses.append("run_id = ?")
        params.append(run_id)
    if world_id:
        clauses.append("world_id = ?")
        params.append(world_id)
    if clauses:
        q += " WHERE " + " AND ".join(clauses)
    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    items = []
    for r in rows:
        row = dict(r)
        row["download_url"] = f"/api/artifacts/{row['id']}/file"
        items.append(row)
    return items


init_agent_history_db()
