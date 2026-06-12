"""Knowledge vault — local folder tree + domain-scoped vector memory per world.

Clone or link a GitHub repo into a world's vault folder, ingest markdown/PDF docs
into domain collections, and query across projects. Graph entities link worlds to topics.
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Optional

from memory import graph as kg
from memory import vector_store
from memory.world_templates import facets_for_template, template_for_kind

SUPPORTED_EXT = {".pdf", ".docx", ".txt", ".md", ".markdown", ".rst", ".csv", ".json"}

VAULT_COLLECTIONS = [
    "vault_company",
    "vault_leads",
    "vault_industry",
    "vault_product",
    "vault_clients",
]

DOMAIN_LABELS = {
    "vault_company": "Company research",
    "vault_leads": "Leads & outreach",
    "vault_industry": "Industry & market",
    "vault_product": "Product & solution",
    "vault_clients": "Clients & ICP",
}


def _storage_backend_label() -> str:
    try:
        from integrations.object_storage import s3_enabled
        return "s3" if s3_enabled() else "local"
    except Exception:
        return "local"


def vault_root() -> Path:
    root = os.getenv("KNOWLEDGE_VAULT_ROOT", "./data/knowledge")
    p = Path(root).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def world_vault_path(world_id: str, world_slug: str | None = None) -> Path:
    slug = world_slug or world_id or "unknown"
    slug = re.sub(r"[^a-z0-9-]", "-", slug.lower()).strip("-")[:48]
    p = vault_root() / slug
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_world_structure(world_id: str, world_slug: str, template_id: str) -> dict:
    """Create on-disk folders for each template facet."""
    base = world_vault_path(world_id, world_slug)
    facets = facets_for_template(template_id)
    created = []
    for f in facets:
        folder = base / f["folder"]
        folder.mkdir(parents=True, exist_ok=True)
        readme = folder / "README.md"
        if not readme.exists():
            readme.write_text(
                f"# {f['label']}\n\nDrop research docs for **{f['label']}** here. "
                f"Ingest via Founder OS Vault or `ingest_vault_folder`.\n",
                encoding="utf-8",
            )
        created.append(str(folder.relative_to(vault_root())))
    (base / "README.md").write_text(
        f"# Knowledge vault — {world_slug}\n\n"
        f"Template: `{template_id}`. Link a repo or copy docs into facet folders, then ingest.\n",
        encoding="utf-8",
    )
    return {"vault_path": str(base), "folders": created}


def _chunk(text: str, size: int = 1000, overlap: int = 150) -> list[str]:
    text = " ".join((text or "").split())
    if not text:
        return []
    chunks, i, n = [], 0, len(text)
    step = max(size - overlap, 1)
    while i < n:
        chunks.append(text[i : i + size])
        i += step
    return chunks


def _domain_for_path(relative: str, template_id: str) -> str:
    rel = relative.replace("\\", "/").lower()
    for facet in facets_for_template(template_id):
        if rel.startswith(facet["folder"] + "/") or rel == facet["folder"]:
            return facet["domain"]
    if "lead" in rel or "sales" in rel:
        return "vault_leads"
    if "industry" in rel or "market" in rel:
        return "vault_industry"
    if "client" in rel or "icp" in rel:
        return "vault_clients"
    if "product" in rel or "solution" in rel or "architecture" in rel:
        return "vault_product"
    return "vault_company"


def ingest_file(
    path: str,
    world_id: str,
    world_slug: str,
    template_id: str,
    domain: str | None = None,
) -> dict:
    from integrations import documents as doc_extract

    path = os.path.abspath(path)
    if not os.path.isfile(path):
        return {"error": f"Not a file: {path}"}
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXT:
        return {"error": f"Unsupported type: {ext}"}

    base = world_vault_path(world_id, world_slug)
    try:
        rel = str(Path(path).resolve().relative_to(base.resolve())).replace("\\", "/")
    except ValueError:
        rel = os.path.basename(path)

    collection = domain or _domain_for_path(rel, template_id)
    if collection not in VAULT_COLLECTIONS:
        collection = "vault_company"

    with open(path, "rb") as f:
        raw = f.read()
    text = doc_extract.extract_text(raw, filename=os.path.basename(path), max_chars=300_000)
    chunks = _chunk(text)
    if not chunks:
        return {"error": "No extractable text"}

    source_key = f"{world_id}:{rel}"
    try:
        vector_store.get_collection(collection).delete(where={"source_key": source_key})
    except Exception:
        pass

    for i, ch in enumerate(chunks):
        vector_store.add(
            collection,
            ch,
            metadata={
                "source": os.path.basename(path),
                "source_key": source_key,
                "path": path,
                "relative_path": rel,
                "world_id": world_id,
                "domain": collection,
                "chunk": i,
            },
        )

    title = os.path.basename(path)
    try:
        kg.upsert_entity(world_id, "topic", {"vault_path": str(base)})
        kg.add_relation(world_id, "has_doc", title, src_type="topic", dst_type="other")
        kg.upsert_entity(title, "topic", {"domain": collection, "world_id": world_id})
    except Exception:
        pass

    return {
        "ingested": title,
        "chunks": len(chunks),
        "collection": collection,
        "relative_path": rel,
    }


def ingest_tree(
    root_path: str,
    world_id: str,
    world_slug: str,
    template_id: str,
    recursive: bool = True,
) -> dict:
    root_path = os.path.abspath(root_path)
    if not os.path.isdir(root_path):
        return {"error": f"Not a directory: {root_path}"}
    ingested, errors, total_chunks = [], [], 0
    walker = os.walk(root_path) if recursive else [(root_path, [], os.listdir(root_path))]
    for dirpath, _dirs, files in walker:
        for fn in files:
            if fn.startswith(".") or fn == "README.md":
                continue
            fp = os.path.join(dirpath, fn)
            r = ingest_file(fp, world_id, world_slug, template_id)
            if r.get("chunks"):
                ingested.append(r)
                total_chunks += r["chunks"]
            elif r.get("error") and "Unsupported" not in r["error"]:
                errors.append(r["error"])
    return {
        "files": len(ingested),
        "total_chunks": total_chunks,
        "ingested": ingested[:40],
        "errors": errors[:10],
    }


def link_repo(world_id: str, world_slug: str, repo_path: str, template_id: str) -> dict:
    """Symlink or note a local clone path; ingest if path exists."""
    repo_path = os.path.abspath(repo_path)
    if not os.path.isdir(repo_path):
        return {"error": f"Repo path not found: {repo_path}"}
    base = world_vault_path(world_id, world_slug)
    link = base / "_repo"
    if link.exists() or link.is_symlink():
        try:
            if link.is_symlink() or link.is_file():
                link.unlink()
            else:
                shutil.rmtree(link)
        except Exception:
            pass
    try:
        link.symlink_to(repo_path, target_is_directory=True)
    except OSError:
        # Windows or permission — write pointer file
        (base / "_repo_path.txt").write_text(repo_path, encoding="utf-8")
    result = ingest_tree(repo_path, world_id, world_slug, template_id)
    result["repo_path"] = repo_path
    result["vault_path"] = str(base)
    return result


def search_vault(
    query: str,
    world_id: str | None = None,
    domain: str | None = None,
    n_results: int = 6,
) -> list:
    collections = [domain] if domain and domain in VAULT_COLLECTIONS else VAULT_COLLECTIONS
    hits = []
    for col in collections:
        try:
            for h in vector_store.search(col, query, n_results=n_results):
                meta = h.get("metadata") or {}
                if world_id and meta.get("world_id") not in (world_id, None, ""):
                    if meta.get("world_id") != world_id:
                        continue
                hits.append(h)
        except Exception:
            continue
    hits.sort(key=lambda x: x.get("distance") or 999)
    return hits[: n_results * 2]


def vault_structure(world_id: str, world_slug: str, template_id: str, world: dict | None = None) -> dict:
    from memory.vault_documents import documents_by_facet, effective_facets, list_documents

    base = world_vault_path(world_id, world_slug)
    facets = effective_facets(world or {}, template_id)
    registry_docs = list_documents(world_id)
    docs_by_facet = documents_by_facet(world_id, facets)
    domains_stats = {}
    for col in VAULT_COLLECTIONS:
        try:
            domains_stats[col] = vector_store.get_collection(col).count()
        except Exception:
            domains_stats[col] = 0

    folders = []
    for facet in facets:
        folder = base / facet["folder"]
        files = []
        if folder.is_dir():
            for p in sorted(folder.rglob("*")):
                if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in SUPPORTED_EXT:
                    files.append({
                        "name": p.name,
                        "path": str(p),
                        "relative": str(p.relative_to(base)).replace("\\", "/"),
                    })
        fid = facet.get("id") or facet.get("folder")
        reg = docs_by_facet.get(fid) or []
        folders.append({
            **facet,
            "domain_label": DOMAIN_LABELS.get(facet["domain"], facet["domain"]),
            "file_count": len(files) + len(reg),
            "files": files[:20],
            "documents": reg,
            "exists": folder.is_dir(),
        })

    repo_link = base / "_repo"
    repo_txt = base / "_repo_path.txt"
    repo_path = None
    if repo_link.is_symlink():
        repo_path = str(repo_link.resolve())
    elif repo_txt.exists():
        repo_path = repo_txt.read_text(encoding="utf-8").strip()

    return {
        "world_id": world_id,
        "vault_path": str(base),
        "template_id": template_id,
        "repo_path": repo_path,
        "facets": folders,
        "domain_counts": domains_stats,
        "document_count": len(registry_docs),
        "storage_backend": _storage_backend_label(),
    }


def enrich_world(world: dict) -> dict:
    if not world:
        return world
    w = dict(world)
    template_id = w.get("template") or template_for_kind(w.get("kind", "project"))
    w["template"] = template_id
    w["template_info"] = facets_for_template(template_id)
    return w
