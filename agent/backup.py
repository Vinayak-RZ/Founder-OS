"""Backups of the agent's entire brain.

Everything the agent knows lives under ./data (SQLite DB + Chroma vector store +
world state + generated files). A single disk loss = total amnesia, so we zip the
whole data directory (excluding the backups folder itself) into ./data/backups/
and keep only the most recent N archives.

Used by the nightly scheduler job and by the `backup_now` / `list_backups` tools.
"""
import os
import zipfile
from datetime import datetime

DATA_DIR = "./data"
BACKUP_DIR = "./data/backups"
KEEP = 14  # retain ~2 weeks of nightly backups


def _abs(path: str) -> str:
    return os.path.abspath(path)


def create_backup() -> dict:
    """Zip the data directory (minus backups) into a timestamped archive."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive = os.path.join(BACKUP_DIR, f"founderos_{stamp}.zip")
    backup_abs = _abs(BACKUP_DIR)

    file_count = 0
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(DATA_DIR):
            # Never recurse into the backups directory (avoids zipping zips).
            dirs[:] = [d for d in dirs if _abs(os.path.join(root, d)) != backup_abs]
            for fn in files:
                fp = os.path.join(root, fn)
                if _abs(fp).startswith(backup_abs):
                    continue
                try:
                    zf.write(fp, os.path.relpath(fp, DATA_DIR))
                    file_count += 1
                except (OSError, ValueError):
                    # Locked/transient file (e.g. an open sqlite WAL) — skip it.
                    continue

    removed = _prune()
    size = os.path.getsize(archive) if os.path.exists(archive) else 0
    return {
        "created": True,
        "path": archive,
        "files": file_count,
        "size_bytes": size,
        "size_mb": round(size / 1_048_576, 2),
        "pruned_old": removed,
        "retained": KEEP,
    }


def _prune() -> int:
    """Keep only the newest KEEP archives; return how many were deleted."""
    try:
        archives = sorted(
            (os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR)
             if f.startswith("founderos_") and f.endswith(".zip")),
            key=os.path.getmtime,
            reverse=True,
        )
    except FileNotFoundError:
        return 0
    removed = 0
    for old in archives[KEEP:]:
        try:
            os.remove(old)
            removed += 1
        except OSError:
            pass
    return removed


def list_backups() -> dict:
    """List existing backups, newest first."""
    if not os.path.isdir(BACKUP_DIR):
        return {"backups": [], "count": 0}
    items = []
    for f in os.listdir(BACKUP_DIR):
        if not (f.startswith("founderos_") and f.endswith(".zip")):
            continue
        fp = os.path.join(BACKUP_DIR, f)
        items.append({
            "file": f,
            "size_mb": round(os.path.getsize(fp) / 1_048_576, 2),
            "created": datetime.fromtimestamp(os.path.getmtime(fp)).isoformat(timespec="minutes"),
        })
    items.sort(key=lambda x: x["created"], reverse=True)
    return {"backups": items, "count": len(items)}
