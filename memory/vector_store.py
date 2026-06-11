"""Vector memory backed by Qdrant Cloud.

All semantic memory (conversations, research, notes, outreach, documents, LLM
cache) lives in Qdrant collections. Embeddings use a local fastembed model so no
extra API calls are needed for vectorization.
"""
import logging
import os
import time
import uuid
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

logger = logging.getLogger(__name__)

COLLECTIONS = [
    "conversations", "research", "notes", "outreach", "documents",
    "vault_company", "vault_leads", "vault_industry", "vault_product", "vault_clients",
]
_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_VECTOR_SIZE = 384

_client: Optional[QdrantClient] = None
_embedder = None
_embedder_tried = False
_collections_ready: set[str] = set()


def _qdrant_url() -> str:
    return os.getenv("QDRANT_URL", "").strip().rstrip("/")


def _qdrant_api_key() -> str:
    return os.getenv("QDRANT_API_KEY", "").strip()


def _collection_prefix() -> str:
    prefix = os.getenv("QDRANT_COLLECTION_PREFIX", "").strip()
    return f"{prefix}_" if prefix else ""


def _full_name(name: str) -> str:
    return f"{_collection_prefix()}{name}"


def _get_client() -> QdrantClient:
    global _client
    if _client is not None:
        return _client
    url = _qdrant_url()
    api_key = _qdrant_api_key()
    if not url or not api_key:
        raise RuntimeError(
            "QDRANT_URL and QDRANT_API_KEY must be set in .env "
            "(see .env.example)."
        )
    _client = QdrantClient(url=url, api_key=api_key)
    return _client


def _get_embedder():
    global _embedder, _embedder_tried
    if _embedder_tried:
        return _embedder
    _embedder_tried = True
    try:
        from fastembed import TextEmbedding
        _embedder = TextEmbedding(model_name=_EMBED_MODEL)
        logger.info(f"[vector_store] embedder ready ({_EMBED_MODEL})")
    except Exception as e:
        logger.error(f"[vector_store] embedder unavailable: {e}")
        _embedder = None
    return _embedder


def embed_texts(texts: list[str]) -> list[list[float]]:
    emb = _get_embedder()
    if emb is None:
        raise RuntimeError("Embedding model unavailable; install fastembed.")
    return [vec.tolist() for vec in emb.embed(texts)]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


def _ensure_collection(name: str):
    full = _full_name(name)
    if full in _collections_ready:
        return
    client = _get_client()
    if not client.collection_exists(full):
        client.create_collection(
            collection_name=full,
            vectors_config=qm.VectorParams(
                size=_VECTOR_SIZE,
                distance=qm.Distance.COSINE,
            ),
        )
        logger.info(f"[vector_store] created collection {full}")
    _collections_ready.add(full)


class QdrantCollection:
    """Thin wrapper exposing the small Chroma-like surface rag_tools expects."""

    def __init__(self, name: str):
        self.name = name
        self.full_name = _full_name(name)

    def count(self) -> int:
        _ensure_collection(self.name)
        return _get_client().count(collection_name=self.full_name, exact=True).count

    def delete(self, ids: list = None, where: dict = None):
        _ensure_collection(self.name)
        client = _get_client()
        if ids:
            client.delete(
                collection_name=self.full_name,
                points_selector=qm.PointIdsList(points=ids),
            )
            return
        if where:
            must = []
            for key, value in where.items():
                must.append(
                    qm.FieldCondition(
                        key=key,
                        match=qm.MatchValue(value=value),
                    )
                )
            client.delete(
                collection_name=self.full_name,
                points_selector=qm.FilterSelector(
                    filter=qm.Filter(must=must),
                ),
            )

    def get(self, limit: int = None, include: list = None) -> dict:
        _ensure_collection(self.name)
        client = _get_client()
        want_docs = not include or "documents" in include
        want_meta = not include or "metadatas" in include
        points, _ = client.scroll(
            collection_name=self.full_name,
            limit=limit or 10_000,
            with_payload=True,
            with_vectors=False,
        )
        documents, metadatas, ids = [], [], []
        for pt in points:
            payload = pt.payload or {}
            ids.append(str(pt.id))
            if want_docs:
                documents.append(payload.get("text", ""))
            if want_meta:
                meta = {k: v for k, v in payload.items() if k != "text"}
                metadatas.append(meta)
        out = {"ids": ids}
        if want_docs:
            out["documents"] = documents
        if want_meta:
            out["metadatas"] = metadatas
        return out


def get_collection(name: str) -> QdrantCollection:
    return QdrantCollection(name)


def add(collection_name: str, text: str, metadata: dict = None, doc_id: str = None):
    _ensure_collection(collection_name)
    doc_id = doc_id or str(uuid.uuid4())
    meta = {"timestamp": time.time(), "source": collection_name}
    if metadata:
        meta.update(metadata)
    vector = embed_query(text)
    payload = {"text": text, **meta}
    _get_client().upsert(
        collection_name=_full_name(collection_name),
        points=[
            qm.PointStruct(id=doc_id, vector=vector, payload=payload),
        ],
    )
    return doc_id


def search(collection_name: str, query: str, n_results: int = 5) -> list:
    _ensure_collection(collection_name)
    col = get_collection(collection_name)
    count = col.count()
    if count == 0:
        return []
    vector = embed_query(query)
    hits = _get_client().search(
        collection_name=_full_name(collection_name),
        query_vector=vector,
        limit=min(n_results, count),
        with_payload=True,
    )
    items = []
    for hit in hits:
        payload = hit.payload or {}
        score = float(hit.score or 0.0)
        items.append({
            "text": payload.get("text", ""),
            "metadata": {k: v for k, v in payload.items() if k != "text"},
            "id": str(hit.id),
            "distance": max(0.0, 1.0 - score),
            "collection": collection_name,
        })
    return items


def search_all(query: str, n_results: int = 3) -> list:
    all_results = []
    for col_name in COLLECTIONS:
        results = search(col_name, query, n_results=n_results)
        all_results.extend(results)
    all_results.sort(key=lambda x: x.get("distance") or 999)
    return all_results[: n_results * 2]


def delete(collection_name: str, doc_id: str):
    get_collection(collection_name).delete(ids=[doc_id])


def collections_overview(samples_per: int = 5) -> list:
    """Counts and recent samples per vector collection for the UI."""
    out = []
    for name in COLLECTIONS:
        entry = {"name": name, "count": 0, "samples": []}
        try:
            col = get_collection(name)
            count = col.count()
            entry["count"] = count
            if count:
                for item in get_recent(name, limit=samples_per):
                    entry["samples"].append({
                        "id": item.get("id"),
                        "text": (item.get("text") or "")[:280],
                        "metadata": item.get("metadata") or {},
                    })
        except Exception as e:
            logger.debug(f"[vector_store] overview {name}: {e}")
        out.append(entry)
    return out


def get_recent(collection_name: str, limit: int = 10) -> list:
    col = get_collection(collection_name)
    count = col.count()
    if count == 0:
        return []
    results = col.get(limit=min(limit, count), include=["documents", "metadatas"])
    items = []
    for i, doc in enumerate(results["documents"]):
        items.append({
            "text": doc,
            "metadata": results["metadatas"][i],
            "id": results["ids"][i],
        })
    items.sort(key=lambda x: x["metadata"].get("timestamp", 0), reverse=True)
    return items
