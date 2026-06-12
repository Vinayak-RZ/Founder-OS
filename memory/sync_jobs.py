"""Persistent background-style jobs for batched GitHub vault sync."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Optional

from memory.sql_store import get_conn


def init_sync_jobs_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sync_jobs (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL DEFAULT 'github_repo',
            world_id TEXT NOT NULL,
            link_id INTEGER,
            full_name TEXT NOT NULL,
            branch TEXT DEFAULT 'main',
            world_slug TEXT NOT NULL,
            template_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            file_manifest TEXT NOT NULL DEFAULT '[]',
            cursor INTEGER NOT NULL DEFAULT 0,
            imported INTEGER NOT NULL DEFAULT 0,
            skipped INTEGER NOT NULL DEFAULT 0,
            total_files INTEGER NOT NULL DEFAULT 0,
            errors TEXT NOT NULL DEFAULT '[]',
            message TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_sync_jobs_world ON sync_jobs(world_id);
        """
    )
    conn.commit()
    conn.close()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _row(row) -> dict:
    if not row:
        return {}
    d = dict(row)
    for k in ("created_at", "updated_at"):
        if d.get(k):
            d[k] = str(d[k])
    try:
        d["errors"] = json.loads(d.get("errors") or "[]")
    except json.JSONDecodeError:
        d["errors"] = []
    return d


def _public(job: dict) -> dict:
    total = int(job.get("total_files") or 0)
    cursor = int(job.get("cursor") or 0)
    progress = round(cursor / total, 4) if total else 0.0
    return {
        "id": job["id"],
        "kind": job.get("kind"),
        "status": job.get("status"),
        "world_id": job.get("world_id"),
        "link_id": job.get("link_id"),
        "full_name": job.get("full_name"),
        "total_files": total,
        "cursor": cursor,
        "imported": int(job.get("imported") or 0),
        "skipped": int(job.get("skipped") or 0),
        "progress": progress,
        "done": job.get("status") in ("completed", "failed"),
        "message": job.get("message") or "",
        "errors": (job.get("errors") or [])[:5],
        "updated_at": job.get("updated_at"),
    }


def create_job(
    *,
    world_id: str,
    link_id: int,
    full_name: str,
    branch: str,
    world_slug: str,
    template_id: str,
    manifest: list[dict],
    kind: str = "github_repo",
) -> dict:
    init_sync_jobs_db()
    job_id = uuid.uuid4().hex[:16]
    manifest_json = json.dumps(manifest)
    total = len(manifest)
    conn = get_conn()
    conn.execute(
        """INSERT INTO sync_jobs
           (id, kind, world_id, link_id, full_name, branch, world_slug, template_id,
            status, file_manifest, total_files, message, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)""",
        (
            job_id,
            kind,
            world_id,
            link_id,
            full_name,
            branch or "main",
            world_slug,
            template_id,
            manifest_json,
            total,
            f"Ready to sync {total} files from {full_name}",
            _now(),
        ),
    )
    conn.commit()
    conn.close()
    return get_job(job_id)


def get_job(job_id: str) -> Optional[dict]:
    init_sync_jobs_db()
    conn = get_conn()
    row = conn.execute("SELECT * FROM sync_jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return _row(row) if row else None


def get_manifest(job: dict) -> list[dict]:
    try:
        return json.loads(job.get("file_manifest") or "[]")
    except json.JSONDecodeError:
        return []


def update_job(job_id: str, **fields) -> Optional[dict]:
    init_sync_jobs_db()
    allowed = {
        "status", "cursor", "imported", "skipped", "errors", "message", "file_manifest", "total_files"
    }
    sets = []
    vals = []
    for k, v in fields.items():
        if k not in allowed:
            continue
        if k == "errors" and isinstance(v, list):
            v = json.dumps(v)
        sets.append(f"{k} = ?")
        vals.append(v)
    if not sets:
        return get_job(job_id)
    sets.append("updated_at = ?")
    vals.append(_now())
    vals.append(job_id)
    conn = get_conn()
    conn.execute(f"UPDATE sync_jobs SET {', '.join(sets)} WHERE id = ?", vals)
    conn.commit()
    conn.close()
    return get_job(job_id)


def list_active_for_world(world_id: str) -> list[dict]:
    init_sync_jobs_db()
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM sync_jobs
           WHERE world_id = ? AND status IN ('pending', 'running')
           ORDER BY updated_at DESC LIMIT 10""",
        (world_id,),
    ).fetchall()
    conn.close()
    return [_public(_row(r)) for r in rows]


def public_view(job_id: str) -> Optional[dict]:
    job = get_job(job_id)
    return _public(job) if job else None
