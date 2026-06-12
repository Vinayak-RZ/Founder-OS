"""Build Cytoscape.js graph payloads for the web UI."""
import re

from config import config


def _nid(*parts: str) -> str:
    raw = ":".join(p for p in parts if p)
    return re.sub(r"[^a-zA-Z0-9:_-]", "_", raw)[:120]


def _node(nid: str, label: str, ntype: str, **extra) -> dict:
    data = {"id": nid, "label": label, "type": ntype}
    data.update(extra)
    return {"data": data}


def _edge(src: str, tgt: str, label: str = "", **extra) -> dict:
    data = {"source": src, "target": tgt, "label": label}
    data.update(extra)
    return {"data": data}


def build_runtime_graph(live: dict | None = None, specialists: list | None = None) -> dict:
    """Founder → supervisor → specialists → live tools."""
    live = live or {}
    specialists = specialists or []
    founder = config.my_name or "Founder"
    company = config.company_name or "Company"

    nodes = [
        _node("founder", founder, "founder", subtitle=company),
        _node("supervisor", "Supervisor", "supervisor"),
    ]
    edges = [_edge("founder", "supervisor", "commands")]

    for s in specialists:
        sid = s if isinstance(s, str) else s.get("id", "")
        label = sid.title() if sid else "Agent"
        if isinstance(s, dict):
            label = s.get("label") or label
        nid = _nid("agent", sid)
        nodes.append(_node(nid, label, "specialist", agent_id=sid))
        edges.append(_edge("supervisor", nid, "routes"))

    active_actor = live.get("actor") or ""
    seen_tools = set()
    for ev in live.get("events") or []:
        if ev.get("type") == "tool" and ev.get("name"):
            tname = ev["name"]
            tid = _nid("tool", tname)
            if tid not in seen_tools:
                seen_tools.add(tid)
                nodes.append(_node(tid, tname, "tool", decision=ev.get("decision", "")))
            if active_actor.startswith("subagent:"):
                src = _nid("agent", active_actor.split(":", 1)[-1])
            elif active_actor == "user":
                src = "supervisor"
            else:
                src = "supervisor"
            edges.append(_edge(src, tid, ev.get("decision") or "run"))
        elif ev.get("type") == "phase" and live.get("active"):
            pass

    if live.get("active") and active_actor.startswith("subagent:"):
        aid = active_actor.split(":", 1)[-1]
        anode = _nid("agent", aid)
        for n in nodes:
            if n["data"]["id"] == anode:
                n["data"]["status"] = "busy"
        for n in nodes:
            if n["data"]["id"] == "supervisor":
                n["data"]["status"] = "routing"

    return {"nodes": nodes, "edges": edges, "meta": {"active": bool(live.get("active"))}}


def build_world_hierarchy_graph(world_tree: dict | None = None) -> dict:
    """Clean founder → main world → sub-worlds tree for the Worlds UI."""
    world_tree = world_tree or {}
    founder = config.my_name or "Founder"
    root_w = world_tree.get("root")
    children = world_tree.get("children") or []

    nodes = [_node("founder", founder, "founder")]
    edges = []

    if not root_w:
        return {"nodes": nodes, "edges": edges}

    rid = _nid("world", root_w.get("id", "root"))
    nodes.append(
        _node(
            rid,
            root_w.get("name", "Main world"),
            "world_root",
            world_id=root_w.get("id", "root"),
            kind="root",
        )
    )
    edges.append(_edge("founder", rid, "operates"))

    for c in children:
        wid = c.get("id", "")
        cid = _nid("world", wid)
        kind = c.get("kind", "project")
        nodes.append(
            _node(
                cid,
                c.get("name", "World"),
                "world_child",
                world_id=wid,
                kind=kind,
            )
        )
        edges.append(_edge(rid, cid, kind))

    return {"nodes": nodes, "edges": edges}


def build_world_graph(snapshot: dict | None = None, goals: list | None = None,
                      world_tree: dict | None = None) -> dict:
    """Business world: hierarchy + founder, company, CRM, goals, tasks."""
    snap = snapshot or {}
    goals = goals or []
    founder = config.my_name or "Founder"
    company = config.company_name or "Company"
    world_tree = world_tree or {}

    nodes = []
    edges = []

    root_w = world_tree.get("root")
    children = world_tree.get("children") or []
    if root_w:
        rid = _nid("world", root_w.get("id", "root"))
        nodes.append(_node(rid, root_w.get("name", "Main world"), "world_root"))
        nodes.append(_node("founder", founder, "founder"))
        edges.append(_edge("founder", rid, "owns"))
        for c in children:
            cid = _nid("world", c.get("id", ""))
            nodes.append(_node(cid, c.get("name", "World"), "world_child", kind=c.get("kind", "")))
            edges.append(_edge(rid, cid, c.get("kind") or "contains"))
        nodes.append(_node("company", company, "company"))
        edges.append(_edge(rid, "company", "ventures"))
    else:
        nodes = [
            _node("founder", founder, "founder"),
            _node("company", company, "company"),
        ]
        edges = [_edge("founder", "company", "runs")]

    crm = snap.get("crm") or {}
    hub = _node("crm", f"CRM ({crm.get('total_contacts', 0)})", "hub")
    nodes.append(hub)
    edges.append(_edge("company", "crm", "pipeline"))

    for status, count in (crm.get("by_status") or {}).items():
        if not count:
            continue
        sid = _nid("status", status)
        nodes.append(_node(sid, f"{status} ({count})", "crm_status"))
        edges.append(_edge("crm", sid, "status"))

    if crm.get("followups_due"):
        fid = "followups"
        nodes.append(_node(fid, f"Follow-ups ({crm['followups_due']})", "alert"))
        edges.append(_edge("crm", fid, "due"))

    tasks_n = snap.get("tasks_open") or 0
    if tasks_n:
        nodes.append(_node("tasks", f"Tasks ({tasks_n})", "tasks"))
        edges.append(_edge("founder", "tasks", "open"))

    appr = snap.get("approvals_pending") or 0
    if appr:
        nodes.append(_node("approvals", f"Approvals ({appr})", "alert"))
        edges.append(_edge("founder", "approvals", "pending"))

    rems = snap.get("reminders_pending") or 0
    if rems:
        nodes.append(_node("reminders", f"Reminders ({rems})", "reminders"))
        edges.append(_edge("founder", "reminders", "scheduled"))

    for i, g in enumerate((snap.get("goals_active") or [])[:6]):
        if isinstance(g, str):
            title = g
        else:
            title = g.get("title", str(g))
        gid = _nid("goal", str(i), title[:20])
        nodes.append(_node(gid, title[:40], "goal"))
        edges.append(_edge("founder", gid, "pursues"))

    for p in (snap.get("projects_open") or [])[:5]:
        pid = _nid("project", str(p.get("id", "")))
        label = (p.get("goal") or "Project")[:36]
        prog = p.get("progress", "")
        nodes.append(_node(pid, f"{label} ({prog})", "project"))
        edges.append(_edge("company", pid, "project"))

    fin = snap.get("finance") or {}
    if fin.get("set"):
        nodes.append(_node("finance", "Finance", "finance", status=fin.get("status", "")))
        edges.append(_edge("company", "finance", "runway"))

    for s in (snap.get("top_strategies") or [])[:4]:
        sid = _nid("strategy", s.get("group", ""), s.get("variant", ""))
        nodes.append(_node(sid, f"{s.get('group')}/{s.get('variant')}", "strategy"))
        edges.append(_edge("founder", sid, "experiments"))

    return {"nodes": nodes, "edges": edges, "meta": {"updated": snap.get("ts")}}


def build_memory_graph(kg: dict | None = None, collections: list | None = None) -> dict:
    """Knowledge graph entities + vector memory collection hubs."""
    kg = kg or {}
    collections = collections or []
    nodes = []
    edges = []
    seen = set()

    for ent in kg.get("entities") or []:
        name = ent.get("name") or ""
        etype = ent.get("type") or "other"
        nid = _nid("kg", etype, name)
        if nid in seen:
            continue
        seen.add(nid)
        nodes.append(_node(nid, name[:40], etype))

    id_by_name_type = {}
    for ent in kg.get("entities") or []:
        name = ent.get("name") or ""
        etype = ent.get("type") or "other"
        id_by_name_type[(name, etype)] = _nid("kg", etype, name)

    for rel in kg.get("relations") or []:
        src = id_by_name_type.get((rel.get("src"), rel.get("src_type")))
        dst = id_by_name_type.get((rel.get("dst"), rel.get("dst_type")))
        if not src or not dst:
            src = _nid("kg", rel.get("src_type", "other"), rel.get("src", ""))
            dst = _nid("kg", rel.get("dst_type", "other"), rel.get("dst", ""))
        if src not in seen:
            seen.add(src)
            nodes.append(_node(src, (rel.get("src") or "")[:40], rel.get("src_type", "other")))
        if dst not in seen:
            seen.add(dst)
            nodes.append(_node(dst, (rel.get("dst") or "")[:40], rel.get("dst_type", "other")))
        edges.append(_edge(src, dst, rel.get("rel") or "related"))

    for col in collections:
        cname = col.get("name") or "memory"
        cid = _nid("collection", cname)
        count = col.get("count") or 0
        nodes.append(_node(cid, f"{cname} ({count})", "collection"))
        for i, sample in enumerate(col.get("samples") or []):
            sid = _nid("mem", cname, str(sample.get("id") or i))
            preview = (sample.get("text") or "")[:48].replace("\n", " ")
            if not preview:
                continue
            nodes.append(_node(sid, preview, "memory_chunk"))
            edges.append(_edge(cid, sid, "contains"))

    if not nodes:
        nodes.append(_node("memory_empty", "No memory yet", "empty"))
    return {"nodes": nodes, "edges": edges, "meta": {"entity_count": len(kg.get("entities") or [])}}


def build_vault_graph(vault: dict | None = None, world: dict | None = None) -> dict:
    """World vault: world → facet folders → documents / disk files + GitHub repos."""
    vault = vault or {}
    world = world or {}
    nodes = []
    edges = []

    wid = world.get("id") or vault.get("world_id") or "world"
    wname = (world.get("name") or "World")[:36]
    world_nid = _nid("vault_world", wid)
    nodes.append(_node(world_nid, wname, "world_root", world_id=wid))

    facets = vault.get("facets") or vault.get("folders") or []
    doc_total = 0
    for facet in facets:
        fid = facet.get("id") or facet.get("folder") or "slot"
        fnid = _nid("vault_facet", wid, fid)
        label = (facet.get("label") or facet.get("folder") or "Folder")[:28]
        count = facet.get("file_count") or 0
        nodes.append(_node(fnid, f"{label} ({count})", "vault_facet", facet_id=fid, folder=facet.get("folder")))
        edges.append(_edge(world_nid, fnid, "folder"))

        for doc in (facet.get("documents") or [])[:14]:
            doc_total += 1
            did = _nid("vault_doc", str(doc.get("id", doc_total)))
            title = (doc.get("title") or doc.get("filename") or "Document")[:36]
            nodes.append(
                _node(
                    did,
                    title,
                    "vault_file",
                    doc_id=doc.get("id"),
                    facet_id=fid,
                    source=doc.get("source_type") or "upload",
                )
            )
            edges.append(_edge(fnid, did, "doc"))

        for i, disk in enumerate((facet.get("files") or [])[:8]):
            name = (disk.get("name") or disk.get("relative") or "file")[:32]
            disk_nid = _nid("vault_disk", wid, fid, str(i))
            nodes.append(_node(disk_nid, name, "vault_file", path=disk.get("relative"), facet_id=fid, source="disk"))
            edges.append(_edge(fnid, disk_nid, "disk"))

    for repo in (vault.get("github_repos") or [])[:10]:
        rid = _nid("gh_repo", str(repo.get("id", "")))
        short = (repo.get("full_name") or "repo").split("/")[-1][:28]
        nodes.append(_node(rid, short, "vault_repo", link_id=repo.get("id"), repo=repo.get("full_name")))
        edges.append(_edge(world_nid, rid, "github"))

    meta = {
        "document_count": vault.get("document_count") or doc_total,
        "facet_count": len(facets),
        "repo_count": len(vault.get("github_repos") or []),
    }
    if len(nodes) <= 1:
        nodes.append(_node("vault_empty", "Add docs or link GitHub", "empty"))
        edges.append(_edge(world_nid, "vault_empty", "start"))

    return {"nodes": nodes, "edges": edges, "meta": meta}
