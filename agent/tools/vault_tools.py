"""Knowledge vault tools — per-world doc folders and domain-scoped RAG."""
from agent.registry import register
from memory import knowledge_vault, worlds
from memory.world_templates import template_for_kind


def _world_ctx(world_id: str | None) -> tuple:
    wid = worlds.resolve_world_id(world_id) if world_id else worlds.ROOT_ID
    if wid == worlds.ROOT_ID:
        return None, None, None, {"error": "Select a sub-world (not main) for vault operations."}
    w = worlds.get(wid)
    if not w:
        return None, None, None, {"error": f"Unknown world: {world_id}"}
    tpl = w.get("template") or template_for_kind(w.get("kind", "project"))
    return w["id"], w.get("slug") or w["id"], tpl, None


@register(
    name="query_vault",
    description="Search the knowledge vault across linked project docs (by domain: company, "
                "leads, industry, product, clients). Use for grounded answers about a world's "
                "research repository. Pass world_id when scoped to one venture.",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "world_id": {"type": "string", "description": "Sub-world id (optional filter)."},
            "domain": {
                "type": "string",
                "description": "Optional: vault_company, vault_leads, vault_industry, vault_product, vault_clients",
            },
            "k": {"type": "integer", "description": "Results per domain (default 5)."},
        },
        "required": ["question"],
    },
    category="research",
)
def query_vault(question, world_id=None, domain=None, k=5):
    wid = worlds.resolve_world_id(world_id) if world_id else None
    if wid == worlds.ROOT_ID:
        wid = None
    hits = knowledge_vault.search_vault(question, world_id=wid, domain=domain, n_results=max(1, min(int(k or 5), 12)))
    if not hits:
        return {"answer_context": [], "message": "No vault hits. Link a repo and ingest docs first."}
    passages = []
    for h in hits:
        meta = h.get("metadata") or {}
        passages.append({
            "text": (h.get("text") or "")[:500],
            "source": meta.get("source"),
            "world_id": meta.get("world_id"),
            "domain": meta.get("domain"),
            "path": meta.get("relative_path") or meta.get("path"),
            "score": h.get("distance"),
        })
    return {"passages": passages, "count": len(passages)}


@register(
    name="vault_structure",
    description="List a world's knowledge vault folders, files on disk, and vector counts per domain.",
    parameters={
        "type": "object",
        "properties": {"world_id": {"type": "string"}},
        "required": ["world_id"],
    },
    category="research",
)
def vault_structure(world_id):
    wid, slug, tpl, err = _world_ctx(world_id)
    if err:
        return err
    return knowledge_vault.vault_structure(wid, slug, tpl)


@register(
    name="ingest_vault_folder",
    description="Ingest all supported documents from a folder into the world's vault "
                "(domain inferred from subfolder). Use after cloning a docs repo.",
    parameters={
        "type": "object",
        "properties": {
            "world_id": {"type": "string"},
            "path": {"type": "string", "description": "Folder path (defaults to world vault root)."},
            "recursive": {"type": "boolean"},
        },
        "required": ["world_id"],
    },
    category="research",
)
def ingest_vault_folder(world_id, path=None, recursive=True):
    wid, slug, tpl, err = _world_ctx(world_id)
    if err:
        return err
    root = path or str(knowledge_vault.world_vault_path(wid, slug))
    return knowledge_vault.ingest_tree(root, wid, slug, tpl, recursive=bool(recursive))


@register(
    name="link_world_repo",
    description="Link a local git clone path to a world's vault and ingest all docs.",
    parameters={
        "type": "object",
        "properties": {
            "world_id": {"type": "string"},
            "repo_path": {"type": "string", "description": "Absolute path to cloned repo."},
        },
        "required": ["world_id", "repo_path"],
    },
    category="research",
)
def link_world_repo(world_id, repo_path):
    wid, slug, tpl, err = _world_ctx(world_id)
    if err:
        return err
    worlds.update_world(wid, repo_path=repo_path)
    return knowledge_vault.link_repo(wid, slug, repo_path, tpl)
