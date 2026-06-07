"""Tool-RAG: retrieve the most relevant tools for a turn instead of sending all.

The top-level agent has many tools (and can author more at runtime). Sending every
schema on every call wastes tokens and dilutes the model's tool choice. Instead we
embed each tool's name + description once, and per turn retrieve the top-k most
relevant tools — unioned with a small always-on CORE set so the agent never loses
essential capabilities (memory, delegation, self-knowledge).

Embeddings reuse Chroma's bundled local model (no network, no new dependency) and
are cached in memory; the cache rebuilds whenever the tool set changes (e.g. after
`create_tool`). If the embedder is unavailable it degrades to a dependency-free
lexical (token-overlap) ranker, and on any hard failure it falls back to the full
catalog — so tool access is never silently lost.
"""
import logging
import re

from agent import registry
from config import config

logger = logging.getLogger(__name__)

# Always offered, regardless of the query — the agent's reflexes.
_CORE = {
    "search_memory", "deep_recall", "save_memory", "world_state",
    "delegate", "delegate_parallel", "about_self",
}

_embed = None
_embed_tried = False
_vecs = None          # {tool_name: normalized np.ndarray}
_vec_sig = None
_TOKEN = re.compile(r"[a-z0-9]+")


def _signature(tools) -> tuple:
    return tuple(sorted((t.name, len(t.description or "")) for t in tools))


def _tok(text: str) -> list:
    return _TOKEN.findall((text or "").lower())


def _get_embedder():
    global _embed, _embed_tried
    if _embed_tried:
        return _embed
    _embed_tried = True
    try:
        from chromadb.utils import embedding_functions
        _embed = embedding_functions.DefaultEmbeddingFunction()
    except Exception as e:
        logger.info(f"[tool_retrieval] embedder unavailable ({e}); lexical fallback.")
        _embed = None
    return _embed


def _normalize(v):
    import numpy as np
    a = np.asarray(v, dtype="float32")
    n = np.linalg.norm(a)
    return a / n if n else a


def _ensure_vectors():
    """Embed the current tool set, caching until the set changes."""
    global _vecs, _vec_sig
    tools = registry.all_tools()
    sig = _signature(tools)
    if _vecs is not None and sig == _vec_sig:
        return _vecs
    emb = _get_embedder()
    if emb is None:
        _vecs, _vec_sig = None, sig
        return None
    docs = [f"{t.name}. {t.description} (category: {t.category})" for t in tools]
    try:
        raw = emb(docs)
    except Exception as e:
        logger.debug(f"[tool_retrieval] embedding failed: {e}")
        _vecs, _vec_sig = None, sig
        return None
    _vecs = {t.name: _normalize(r) for t, r in zip(tools, raw)}
    _vec_sig = sig
    logger.info(f"[tool_retrieval] embedded {len(_vecs)} tools")
    return _vecs


def _lexical(message: str, k: int) -> set:
    """Dependency-free fallback: rank tools by token overlap with the message."""
    qt = set(_tok(message))
    if not qt:
        return set()
    scored = []
    for t in registry.all_tools():
        dt = set(_tok(f"{t.name} {t.description} {t.category}"))
        overlap = len(qt & dt)
        if overlap:
            scored.append((overlap, t.name))
    scored.sort(reverse=True)
    return {name for _, name in scored[:k]}


def relevant_tool_names(message: str, k: int) -> set:
    vecs = _ensure_vectors()
    if not vecs:
        return _lexical(message, k)
    try:
        import numpy as np
        emb = _get_embedder()
        q = _normalize(emb([message])[0])
        scored = sorted(vecs.items(), key=lambda kv: float(np.dot(q, kv[1])), reverse=True)
        return {name for name, _ in scored[:k]}
    except Exception as e:
        logger.debug(f"[tool_retrieval] query failed: {e}")
        return _lexical(message, k)


def schemas_for_message(message: str, k: int = None) -> list:
    """Return tool schemas relevant to `message` (+ CORE), or all tools on fallback."""
    if not getattr(config, "tool_rag", True):
        return registry.all_schemas()
    k = k or getattr(config, "tool_rag_k", 16)
    names = relevant_tool_names(message, k) | _CORE
    tools = [t for t in registry.all_tools() if t.name in names]
    # If retrieval degraded badly, never starve the agent.
    if len(tools) < 4:
        return registry.all_schemas()
    return [t.schema() for t in tools]
