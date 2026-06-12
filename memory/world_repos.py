"""Multiple GitHub repos linked to a single world."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from memory.sql_store import get_conn


def init_world_repos_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS world_repos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            world_id TEXT NOT NULL,
            full_name TEXT NOT NULL,
            default_branch TEXT DEFAULT 'main',
            private INTEGER DEFAULT 0,
            html_url TEXT DEFAULT '',
            synced_at TIMESTAMP,
            file_count INTEGER DEFAULT 0,
            last_error TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(world_id, full_name)
        );
        CREATE INDEX IF NOT EXISTS idx_world_repos_world ON world_repos(world_id);
        """
    )
    conn.commit()
    conn.close()


def _row(row) -> dict:
    if not row:
        return {}
    d = dict(row)
    for k in ("created_at", "synced_at"):
        if d.get(k):
            d[k] = str(d[k])
    d["private"] = bool(d.get("private"))
    return d


def list_repos(world_id: str) -> list:
    init_world_repos_db()
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM world_repos WHERE world_id = ? ORDER BY created_at DESC",
        (world_id,),
    ).fetchall()
    conn.close()
    return [_row(r) for r in rows]


def get_repo_link(link_id: int) -> Optional[dict]:
    init_world_repos_db()
    conn = get_conn()
    row = conn.execute("SELECT * FROM world_repos WHERE id = ?", (link_id,)).fetchone()
    conn.close()
    return _row(row) if row else None


def add_repo(world_id: str, full_name: str, *, default_branch: str = "main", private: bool = False, html_url: str = "") -> dict:
    init_world_repos_db()
    full_name = (full_name or "").strip()
    if "/" not in full_name:
        raise ValueError("full_name must be owner/repo")
    conn = get_conn()
    try:
        conn.execute(
            """INSERT INTO world_repos (world_id, full_name, default_branch, private, html_url)
               VALUES (?, ?, ?, ?, ?)""",
            (world_id, full_name, default_branch or "main", int(private), html_url or ""),
        )
        conn.commit()
    except Exception as e:
        conn.close()
        if "UNIQUE" in str(e):
            raise ValueError(f"Repo already linked: {full_name}") from e
        raise
    row_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.close()
    return get_repo_link(row_id)


def update_repo_sync(link_id: int, file_count: int, error: str = "") -> None:
    init_world_repos_db()
    now = datetime.now().isoformat(timespec="seconds")
    conn = get_conn()
    conn.execute(
        "UPDATE world_repos SET synced_at = ?, file_count = ?, last_error = ? WHERE id = ?",
        (now, file_count, error or "", link_id),
    )
    conn.commit()
    conn.close()


def remove_repo(link_id: int, world_id: str) -> bool:
    init_world_repos_db()
    conn = get_conn()
    cur = conn.execute("DELETE FROM world_repos WHERE id = ? AND world_id = ?", (link_id, world_id))
    conn.commit()
    conn.close()
    return cur.rowcount > 0
