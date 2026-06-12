"""Sync GitHub repository files into world vault (S3/local) + vector catalog."""
from __future__ import annotations

import os
from typing import Optional

from integrations import github_client
from memory import vault_documents as vd
from memory.world_templates import facets_for_template

SYNC_MAX_FILES = 200
SYNC_MAX_BYTES = 2_000_000
SUPPORTED_EXT = vd.SUPPORTED_EXT


def _facet_for_path(relative: str, template_id: str) -> str:
    rel = relative.replace("\\", "/").lower()
    for f in facets_for_template(template_id):
        folder = (f.get("folder") or "").lower()
        fid = f.get("id") or f.get("folder") or "docs"
        if folder and (rel.startswith(folder + "/") or rel == folder):
            return fid
    if any(x in rel for x in ("icp", "client")):
        return "clients"
    if any(x in rel for x in ("gtm", "marketing")):
        return "gtm"
    if any(x in rel for x in ("readme", "doc")):
        return "docs"
    return "docs"


def _description_from_text(text: str, max_len: int = 400) -> str:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    body = " ".join(lines[:6])
    if len(body) > max_len:
        return body[: max_len - 1] + "…"
    return body or "Imported from GitHub"


def _title_from_path(path: str) -> str:
    base = os.path.basename(path)
    name, ext = os.path.splitext(base)
    if ext.lower() in (".md", ".markdown"):
        return name.replace("-", " ").replace("_", " ").title()
    return base


def sync_repo_to_world(
    world_id: str,
    world_slug: str,
    template_id: str,
    full_name: str,
    branch: str | None = None,
    link_id: Optional[int] = None,
) -> dict:
    from memory import world_repos

    blobs = github_client.list_repo_tree(full_name, branch)
    imported, skipped, errors = 0, 0, []

    for item in blobs[: SYNC_MAX_FILES * 2]:
        if imported >= SYNC_MAX_FILES:
            break
        path = item["path"]
        size = item.get("size") or 0
        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_EXT:
            skipped += 1
            continue
        if size > SYNC_MAX_BYTES:
            skipped += 1
            continue
        if path.split("/")[-1].startswith("."):
            skipped += 1
            continue
        try:
            raw = github_client.fetch_file_bytes(full_name, path, ref=branch)
            if len(raw) > SYNC_MAX_BYTES:
                skipped += 1
                continue
            text_preview = raw.decode("utf-8", errors="replace")
            facet_id = _facet_for_path(path, template_id)
            title = _title_from_path(path)
            description = _description_from_text(text_preview)
            source_ref = f"github:{full_name}:{path}"
            vd.upsert_github_document(
                world_id=world_id,
                world_slug=world_slug,
                template_id=template_id,
                facet_id=facet_id,
                title=title,
                description=description,
                filename=os.path.basename(path),
                file_bytes=raw,
                source_ref=source_ref,
                github_repo=full_name,
                github_path=path,
            )
            imported += 1
        except Exception as e:
            errors.append(f"{path}: {e}")

    if link_id:
        world_repos.update_repo_sync(link_id, imported, "; ".join(errors[:3]))

    return {
        "full_name": full_name,
        "imported": imported,
        "skipped": skipped,
        "errors": errors[:10],
    }
