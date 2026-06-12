"""Vault document registry — metadata in SQLite, payloads in S3/local, descriptions in vector DB."""
from __future__ import annotations

import json
import mimetypes
import os
import re
import uuid
from datetime import datetime
from typing import Optional

from integrations import object_storage
from memory.sql_store import get_conn
from memory import vector_store
from memory.world_templates import facets_for_template

SUPPORTED_EXT = {".pdf", ".docx", ".txt", ".md", ".markdown", ".rst", ".csv", ".json"}


def init_vault_documents_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS vault_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            world_id TEXT NOT NULL,
            facet_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            storage_key TEXT NOT NULL,
            storage_backend TEXT DEFAULT 'local',
            filename TEXT DEFAULT '',
            mime_type TEXT DEFAULT '',
            size_bytes INTEGER DEFAULT 0,
            domain TEXT DEFAULT 'vault_company',
            relative_path TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_vault_docs_world ON vault_documents(world_id);
        CREATE INDEX IF NOT EXISTS idx_vault_docs_facet ON vault_documents(world_id, facet_id);
        """
    )
    for col, typedef in (
        ("source_type", "TEXT DEFAULT 'upload'"),
        ("source_ref", "TEXT DEFAULT ''"),
        ("github_repo", "TEXT DEFAULT ''"),
        ("github_path", "TEXT DEFAULT ''"),
    ):
        try:
            conn.execute(f"ALTER TABLE vault_documents ADD COLUMN {col} {typedef}")
        except Exception:
            pass
    conn.commit()
    conn.close()


def _row(row) -> dict:
    if not row:
        return {}
    d = dict(row)
    for k in ("created_at", "updated_at"):
        if d.get(k):
            d[k] = str(d[k])
    return d


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", (s or "").lower()).strip("-")[:48] or "doc"


def _domain_for_facet(facet_id: str, template_id: str) -> str:
    for f in facets_for_template(template_id):
        if f.get("id") == facet_id or f.get("folder") == facet_id:
            return f.get("domain") or "vault_company"
    return "vault_company"


def _catalog_source_key(world_id: str, doc_id: int) -> str:
    return f"catalog:{world_id}:{doc_id}"


def index_catalog_entry(doc: dict) -> None:
    """Index title + description only — full doc lives in object storage."""
    collection = doc.get("domain") or "vault_company"
    doc_id = doc["id"]
    world_id = doc["world_id"]
    source_key = _catalog_source_key(world_id, doc_id)
    text = f"{doc.get('title') or 'Untitled'}\n\n{doc.get('description') or ''}".strip()
    if not text:
        return
    try:
        vector_store.get_collection(collection).delete(where={"source_key": source_key})
    except Exception:
        pass
    vector_store.add(
        collection,
        text,
        metadata={
            "source_key": source_key,
            "doc_id": doc_id,
            "world_id": world_id,
            "facet_id": doc.get("facet_id") or "",
            "storage_key": doc.get("storage_key") or "",
            "title": doc.get("title") or "",
            "catalog_only": True,
            "domain": collection,
        },
    )


def unindex_catalog_entry(doc: dict) -> None:
    collection = doc.get("domain") or "vault_company"
    source_key = _catalog_source_key(doc["world_id"], doc["id"])
    try:
        vector_store.get_collection(collection).delete(where={"source_key": source_key})
    except Exception:
        pass


def list_documents(world_id: str, facet_id: str | None = None) -> list:
    init_vault_documents_db()
    conn = get_conn()
    if facet_id:
        rows = conn.execute(
            "SELECT * FROM vault_documents WHERE world_id = ? AND facet_id = ? ORDER BY updated_at DESC",
            (world_id, facet_id),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM vault_documents WHERE world_id = ? ORDER BY facet_id, updated_at DESC",
            (world_id,),
        ).fetchall()
    conn.close()
    return [_row(r) for r in rows]


def get_document(doc_id: int) -> Optional[dict]:
    init_vault_documents_db()
    conn = get_conn()
    row = conn.execute("SELECT * FROM vault_documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()
    return _row(row) if row else None


def create_document(
    world_id: str,
    world_slug: str,
    template_id: str,
    facet_id: str,
    title: str,
    description: str = "",
    *,
    file_bytes: bytes | None = None,
    filename: str = "",
    text_content: str | None = None,
) -> dict:
    init_vault_documents_db()
    title = (title or "").strip()
    if not title:
        raise ValueError("title is required")
    facet_id = (facet_id or "docs").strip()
    domain = _domain_for_facet(facet_id, template_id)

    if file_bytes is None and text_content is not None:
        filename = filename or f"{_slug(title)}.md"
        file_bytes = text_content.encode("utf-8")
    if not file_bytes:
        raise ValueError("file or text_content is required")

    fn = filename or f"{_slug(title)}.bin"
    ext = os.path.splitext(fn)[1].lower()
    if ext and ext not in SUPPORTED_EXT:
        raise ValueError(f"unsupported file type: {ext}")

    doc_uid = uuid.uuid4().hex[:10]
    storage_key = f"worlds/{world_id}/{facet_id}/{doc_uid}/{fn}"
    mime = mimetypes.guess_type(fn)[0] or "application/octet-stream"
    stored = object_storage.put_bytes(storage_key, file_bytes, mime)
    if stored.get("error"):
        raise RuntimeError(stored["error"])

    relative_path = f"{facet_id}/{fn}"
    now = datetime.now().isoformat(timespec="seconds")
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO vault_documents
           (world_id, facet_id, title, description, storage_key, storage_backend,
            filename, mime_type, size_bytes, domain, relative_path, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            world_id,
            facet_id,
            title,
            (description or "").strip(),
            storage_key,
            stored.get("backend") or "local",
            fn,
            mime,
            len(file_bytes),
            domain,
            relative_path,
            now,
        ),
    )
    conn.commit()
    doc_id = cur.lastrowid
    conn.close()

    doc = get_document(doc_id)
    try:
        index_catalog_entry(doc)
    except Exception:
        pass

    # Mirror into on-disk facet folder for visibility
    try:
        from memory import knowledge_vault

        base = knowledge_vault.world_vault_path(world_id, world_slug)
        folder = base / facet_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / fn).write_bytes(file_bytes)
    except Exception:
        pass

    return doc


def update_document(
    doc_id: int,
    *,
    title: str | None = None,
    description: str | None = None,
    facet_id: str | None = None,
    text_content: str | None = None,
    template_id: str = "startup",
) -> Optional[dict]:
    init_vault_documents_db()
    doc = get_document(doc_id)
    if not doc:
        return None

    updates = {}
    if title is not None:
        updates["title"] = title.strip()
    if description is not None:
        updates["description"] = description.strip()
    if facet_id is not None:
        updates["facet_id"] = facet_id.strip()
        updates["domain"] = _domain_for_facet(facet_id, template_id)

    if text_content is not None:
        data = text_content.encode("utf-8")
        stored = object_storage.put_bytes(doc["storage_key"], data, doc.get("mime_type") or "text/markdown")
        if stored.get("error"):
            raise RuntimeError(stored["error"])
        updates["size_bytes"] = len(data)
        updates["storage_backend"] = stored.get("backend") or doc.get("storage_backend")

    if not updates:
        return doc

    updates["updated_at"] = datetime.now().isoformat(timespec="seconds")
    sets = ", ".join(f"{k} = ?" for k in updates)
    conn = get_conn()
    conn.execute(f"UPDATE vault_documents SET {sets} WHERE id = ?", (*updates.values(), doc_id))
    conn.commit()
    conn.close()

    doc = get_document(doc_id)
    try:
        index_catalog_entry(doc)
    except Exception:
        pass
    return doc


def delete_document(doc_id: int) -> bool:
    init_vault_documents_db()
    doc = get_document(doc_id)
    if not doc:
        return False
    try:
        unindex_catalog_entry(doc)
    except Exception:
        pass
    if doc.get("storage_key"):
        object_storage.delete_object(doc["storage_key"])
    conn = get_conn()
    conn.execute("DELETE FROM vault_documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()
    return True


def get_by_source_ref(world_id: str, source_ref: str) -> Optional[dict]:
    init_vault_documents_db()
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM vault_documents WHERE world_id = ? AND source_ref = ?",
        (world_id, source_ref),
    ).fetchone()
    conn.close()
    return _row(row) if row else None


def delete_documents_for_github_repo(world_id: str, full_name: str) -> int:
    init_vault_documents_db()
    prefix = f"github:{full_name}:"
    conn = get_conn()
    rows = conn.execute(
        "SELECT id FROM vault_documents WHERE world_id = ? AND source_ref LIKE ?",
        (world_id, prefix + "%"),
    ).fetchall()
    conn.close()
    n = 0
    for r in rows:
        if delete_document(r["id"]):
            n += 1
    return n


def upsert_github_document(
    *,
    world_id: str,
    world_slug: str,
    template_id: str,
    facet_id: str,
    title: str,
    description: str,
    filename: str,
    file_bytes: bytes,
    source_ref: str,
    github_repo: str,
    github_path: str,
) -> dict:
    existing = get_by_source_ref(world_id, source_ref)
    if existing:
        stored = object_storage.put_bytes(
            existing["storage_key"],
            file_bytes,
            existing.get("mime_type") or mimetypes.guess_type(filename)[0] or "application/octet-stream",
        )
        if stored.get("error"):
            raise RuntimeError(stored["error"])
        return update_document(
            existing["id"],
            title=title,
            description=description,
            facet_id=facet_id,
            template_id=template_id,
        ) or existing

    doc = create_document(
        world_id,
        world_slug,
        template_id,
        facet_id,
        title,
        description,
        file_bytes=file_bytes,
        filename=filename,
    )
    init_vault_documents_db()
    conn = get_conn()
    conn.execute(
        """UPDATE vault_documents SET source_type = 'github', source_ref = ?,
           github_repo = ?, github_path = ?, relative_path = ? WHERE id = ?""",
        (source_ref, github_repo, github_path, f"github/{github_repo}/{github_path}", doc["id"]),
    )
    conn.commit()
    conn.close()
    return get_document(doc["id"]) or doc


def effective_facets(world: dict, template_id: str) -> list:
    """Template facets, optionally overridden by world.facets_json."""
    raw = world.get("facets_json") or ""
    if raw:
        try:
            custom = json.loads(raw)
            if isinstance(custom, list) and custom:
                return custom
        except (json.JSONDecodeError, TypeError):
            pass
    return facets_for_template(template_id)


def documents_by_facet(world_id: str, facets: list) -> dict:
    docs = list_documents(world_id)
    grouped = {f.get("id") or f.get("folder"): [] for f in facets}
    for d in docs:
        fid = d.get("facet_id") or "docs"
        if fid not in grouped:
            grouped[fid] = []
        grouped[fid].append(d)
    return grouped
