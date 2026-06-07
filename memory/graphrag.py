"""GraphRAG: community detection + summaries over the knowledge graph.

`memory/graph.py` answers LOCAL questions ("who works at Acme?"). GraphRAG answers
GLOBAL/thematic ones ("how is my network clustered?", "which parts of my world touch
fintech?") the way Microsoft's GraphRAG does:

  1. Detect communities in the entity graph with label propagation — a fast,
     dependency-free clustering algorithm (no networkx/torch).
  2. Summarize each community with the LLM into a natural-language description.
  3. Answer global queries by map-reducing the question over the most relevant
     community summaries.

Everything is local (SQLite + the router). Summaries are cached in `kg_communities`
and refreshed on demand or nightly.
"""
import json
import logging
import re
from collections import Counter, defaultdict

from memory.sql_store import get_conn

logger = logging.getLogger(__name__)

_TOKEN = re.compile(r"[a-z0-9]+")


def init_graphrag_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS kg_communities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT,
            members_json TEXT,
            size INTEGER,
            summary TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    conn.close()


def _load_edges() -> list:
    conn = get_conn()
    rows = conn.execute(
        """SELECT e1.name AS src, r.rel AS rel, e2.name AS dst
           FROM kg_relations r
           JOIN kg_entities e1 ON r.src_id = e1.id
           JOIN kg_entities e2 ON r.dst_id = e2.id"""
    ).fetchall()
    conn.close()
    return [(r["src"], r["rel"], r["dst"]) for r in rows]


def _adjacency(edges: list) -> dict:
    adj = defaultdict(set)
    for s, _rel, d in edges:
        if s and d and s != d:
            adj[s].add(d)
            adj[d].add(s)
    return adj


def detect_communities(edges: list, max_iter: int = 30) -> dict:
    """Label propagation. Returns {label: [members]}. Deterministic tie-breaking."""
    adj = _adjacency(edges)
    nodes = sorted(adj.keys())
    labels = {n: n for n in nodes}
    for _ in range(max_iter):
        changed = False
        for n in nodes:
            neigh = adj[n]
            if not neigh:
                continue
            counts = Counter(labels[m] for m in neigh)
            # most frequent neighbor label; tie-break on smallest label name.
            best = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            if labels[n] != best:
                labels[n] = best
                changed = True
        if not changed:
            break
    comms = defaultdict(list)
    for n, lab in labels.items():
        comms[lab].append(n)
    return comms


async def _summarize_community(members: list, edges: list) -> str:
    from llm.router import complete
    mset = set(members)
    internal = [(s, r, d) for s, r, d in edges if s in mset and d in mset]
    rel_lines = "\n".join(f"- {s} --{r}--> {d}" for s, r, d in internal[:60])
    member_line = ", ".join(members[:40])
    messages = [
        {"role": "system", "content":
            "Summarize this cluster of the founder's professional network in 2-3 sentences: "
            "what/who it contains, the dominant theme, and why it matters. Be concrete; do not invent."},
        {"role": "user", "content": f"ENTITIES: {member_line}\n\nRELATIONS:\n{rel_lines or '(none)'}"},
    ]
    return (await complete(messages, task_type="analysis", max_tokens=200)).strip()


async def build_communities(min_size: int = 2, max_communities: int = 15) -> dict:
    """Detect communities and (re)generate their summaries. Returns a report."""
    init_graphrag_db()
    edges = _load_edges()
    comms = detect_communities(edges)
    sized = sorted(((lab, mem) for lab, mem in comms.items() if len(mem) >= min_size),
                   key=lambda kv: len(kv[1]), reverse=True)[:max_communities]

    conn = get_conn()
    conn.execute("DELETE FROM kg_communities")
    conn.commit()
    conn.close()

    out = []
    for lab, mem in sized:
        members = sorted(mem)
        try:
            summary = await _summarize_community(members, edges)
        except Exception as e:
            logger.debug(f"[graphrag] summary failed: {e}")
            summary = f"Cluster of {len(members)} entities: {', '.join(members[:8])}."
        conn = get_conn()
        conn.execute(
            "INSERT INTO kg_communities (label, members_json, size, summary) VALUES (?, ?, ?, ?)",
            (str(lab), json.dumps(members), len(members), summary),
        )
        conn.commit()
        conn.close()
        out.append({"label": str(lab), "size": len(members),
                    "summary": summary, "members": members[:12]})
    return {"communities": len(out), "items": out}


def list_communities() -> list:
    init_graphrag_db()
    conn = get_conn()
    rows = conn.execute(
        "SELECT label, size, summary, members_json FROM kg_communities ORDER BY size DESC"
    ).fetchall()
    conn.close()
    return [{"label": r["label"], "size": r["size"], "summary": r["summary"],
             "members": json.loads(r["members_json"] or "[]")} for r in rows]


def _tok(text: str) -> set:
    return set(_TOKEN.findall((text or "").lower()))


def _rank_communities(question: str, comms: list) -> list:
    qt = _tok(question)
    if not qt:
        return comms
    def score(c):
        text = c["summary"] + " " + " ".join(c.get("members") or [])
        return len(qt & _tok(text))
    return sorted(comms, key=score, reverse=True)


async def global_answer(question: str, top_n: int = 4) -> dict:
    """Answer a big-picture question by map-reducing over community summaries."""
    comms = list_communities()
    if not comms:
        await build_communities()
        comms = list_communities()
    if not comms:
        return {"answer": "The knowledge graph has no communities yet. Add relationships "
                          "with graph_link or sync the CRM, then rebuild the network map.",
                "communities": []}
    ranked = _rank_communities(question, comms)[:top_n]
    context = "\n\n".join(
        f"[Community summary] {c['summary']}\nMembers: {', '.join(c['members'][:10])}"
        for c in ranked)
    from llm.router import complete
    messages = [
        {"role": "system", "content":
            "Answer the question about the founder's network/business using ONLY these "
            "community summaries. If they don't cover it, say so. Be concise and concrete."},
        {"role": "user", "content": f"QUESTION:\n{question}\n\nNETWORK COMMUNITIES:\n{context}"},
    ]
    ans = (await complete(messages, task_type="analysis", max_tokens=400)).strip()
    return {"answer": ans,
            "communities": [{"size": c["size"], "summary": c["summary"]} for c in ranked]}


init_graphrag_db()
