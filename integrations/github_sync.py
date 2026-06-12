"""Batched GitHub repo → vault sync (S3/local + vector catalog)."""
from __future__ import annotations

import os
from typing import Optional

from integrations import github_client
from memory import sync_jobs
from memory import vault_documents as vd
from memory.world_templates import facets_for_template

SYNC_MAX_FILES = 200
SYNC_MAX_BYTES = 2_000_000
SYNC_BATCH_DEFAULT = 8
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


def _is_eligible_blob(path: str, size: int) -> bool:
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXT:
        return False
    if size > SYNC_MAX_BYTES:
        return False
    if path.split("/")[-1].startswith("."):
        return False
    return True


def build_file_manifest(full_name: str, branch: str | None = None) -> tuple[list[dict], int]:
    """Return (eligible files up to cap, skipped count from filters)."""
    blobs = github_client.list_repo_tree(full_name, branch)
    eligible: list[dict] = []
    skipped = 0
    for item in blobs:
        path = item["path"]
        size = item.get("size") or 0
        if not _is_eligible_blob(path, size):
            skipped += 1
            continue
        eligible.append({"path": path, "size": size})
        if len(eligible) >= SYNC_MAX_FILES:
            break
    return eligible, skipped


def import_file(
    *,
    world_id: str,
    world_slug: str,
    template_id: str,
    full_name: str,
    branch: str | None,
    path: str,
) -> None:
    raw = github_client.fetch_file_bytes(full_name, path, ref=branch)
    if len(raw) > SYNC_MAX_BYTES:
        raise ValueError(f"File too large: {path}")
    text_preview = raw.decode("utf-8", errors="replace")
    facet_id = _facet_for_path(path, template_id)
    vd.upsert_github_document(
        world_id=world_id,
        world_slug=world_slug,
        template_id=template_id,
        facet_id=facet_id,
        title=_title_from_path(path),
        description=_description_from_text(text_preview),
        filename=os.path.basename(path),
        file_bytes=raw,
        source_ref=f"github:{full_name}:{path}",
        github_repo=full_name,
        github_path=path,
    )


def start_repo_sync_job(
    *,
    world_id: str,
    world_slug: str,
    template_id: str,
    full_name: str,
    branch: str | None,
    link_id: int,
) -> dict:
    from dashboard import notifications

    try:
        manifest, skipped_prefilter = build_file_manifest(full_name, branch)
    except Exception as e:
        job = sync_jobs.create_job(
            world_id=world_id,
            link_id=link_id,
            full_name=full_name,
            branch=branch or "main",
            world_slug=world_slug,
            template_id=template_id,
            manifest=[],
        )
        sync_jobs.update_job(job["id"], status="failed", message=str(e))
        notifications.push(
            "GitHub sync failed",
            f"Could not read {full_name}: {e}",
            kind="error",
            meta={"world_id": world_id, "repo": full_name},
        )
        return sync_jobs.public_view(job["id"])

    job = sync_jobs.create_job(
        world_id=world_id,
        link_id=link_id,
        full_name=full_name,
        branch=branch or "main",
        world_slug=world_slug,
        template_id=template_id,
        manifest=manifest,
    )
    if skipped_prefilter:
        sync_jobs.update_job(
            job["id"],
            skipped=skipped_prefilter,
            message=f"{len(manifest)} files queued ({skipped_prefilter} skipped by filters)",
        )
    notifications.push(
        "GitHub sync started",
        f"Syncing {len(manifest)} files from {full_name} to your vault",
        kind="info",
        meta={"world_id": world_id, "job_id": job["id"], "repo": full_name},
    )
    return sync_jobs.public_view(job["id"])


def process_sync_batch(job_id: str, batch_size: int = SYNC_BATCH_DEFAULT) -> dict:
    from dashboard import notifications
    from memory import world_repos

    job = sync_jobs.get_job(job_id)
    if not job:
        return {"error": "job not found"}
    if job["status"] in ("completed", "failed"):
        return sync_jobs.public_view(job_id)

    manifest = sync_jobs.get_manifest(job)
    total = len(manifest)
    cursor = int(job.get("cursor") or 0)
    imported = int(job.get("imported") or 0)
    skipped = int(job.get("skipped") or 0)
    errors: list[str] = list(job.get("errors") or [])

    if total == 0:
        sync_jobs.update_job(job_id, status="completed", message="No eligible files to import")
        if job.get("link_id"):
            world_repos.update_repo_sync(int(job["link_id"]), 0, "")
        notifications.push(
            "GitHub sync complete",
            f"No supported files found in {job['full_name']}",
            kind="info",
            meta={"world_id": job["world_id"], "job_id": job_id},
        )
        return sync_jobs.public_view(job_id)

    sync_jobs.update_job(job_id, status="running", message=f"Importing files ({cursor}/{total})…")

    end = min(cursor + max(1, batch_size), total)
    batch = manifest[cursor:end]
    branch = job.get("branch") or "main"

    for item in batch:
        path = item["path"]
        try:
            import_file(
                world_id=job["world_id"],
                world_slug=job["world_slug"],
                template_id=job["template_id"],
                full_name=job["full_name"],
                branch=branch,
                path=path,
            )
            imported += 1
        except Exception as e:
            skipped += 1
            errors.append(f"{path}: {e}")

    cursor = end
    done = cursor >= total
    status = "completed" if done else "running"
    msg = (
        f"Imported {imported} files from {job['full_name']}"
        if done
        else f"Importing… {cursor}/{total} files processed"
    )
    sync_jobs.update_job(
        job_id,
        status=status,
        cursor=cursor,
        imported=imported,
        skipped=skipped,
        errors=errors[:20],
        message=msg,
    )

    if done and job.get("link_id"):
        err_summary = "; ".join(errors[:3])
        world_repos.update_repo_sync(int(job["link_id"]), imported, err_summary)
        kind = "success" if not errors else "warning"
        notifications.push(
            "GitHub sync complete",
            f"{imported} files synced from {job['full_name']}"
            + (f" ({len(errors)} skipped/failed)" if errors else ""),
            kind=kind,
            meta={"world_id": job["world_id"], "job_id": job_id, "repo": job["full_name"]},
        )

    return sync_jobs.public_view(job_id)


def sync_repo_to_world(
    world_id: str,
    world_slug: str,
    template_id: str,
    full_name: str,
    branch: str | None = None,
    link_id: Optional[int] = None,
) -> dict:
    """Legacy one-shot sync — runs all batches inline (tests / scripts)."""
    if not link_id:
        raise ValueError("link_id required")
    job_view = start_repo_sync_job(
        world_id=world_id,
        world_slug=world_slug,
        template_id=template_id,
        full_name=full_name,
        branch=branch,
        link_id=link_id,
    )
    if job_view.get("status") == "failed":
        return {"full_name": full_name, "imported": 0, "skipped": 0, "errors": [job_view.get("message")]}
    job_id = job_view["id"]
    while True:
        result = process_sync_batch(job_id, batch_size=SYNC_BATCH_DEFAULT)
        if result.get("done"):
            return {
                "full_name": full_name,
                "imported": result.get("imported", 0),
                "skipped": result.get("skipped", 0),
                "errors": result.get("errors", []),
                "job_id": job_id,
            }
