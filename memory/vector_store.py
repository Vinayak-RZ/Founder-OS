import os
import time
import uuid

# ChromaDB 0.4.x can emit noisy PostHog telemetry errors on some dependency
# combinations. Disable telemetry before importing chromadb so it never starts.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY_IMPL", "chromadb.telemetry.product.null.NullTelemetry")

import chromadb
from chromadb.config import Settings

os.makedirs("./data/chroma", exist_ok=True)

client = chromadb.PersistentClient(
    path="./data/chroma",
    settings=Settings(anonymized_telemetry=False),
)

COLLECTIONS = ["conversations", "research", "notes", "outreach", "documents"]

def get_collection(name: str):
    return client.get_or_create_collection(name)

def add(collection_name: str, text: str, metadata: dict = None, doc_id: str = None):
    col = get_collection(collection_name)
    doc_id = doc_id or str(uuid.uuid4())
    meta = {"timestamp": time.time(), "source": collection_name}
    if metadata:
        meta.update(metadata)
    col.add(documents=[text], metadatas=[meta], ids=[doc_id])
    return doc_id

def search(collection_name: str, query: str, n_results: int = 5) -> list:
    col = get_collection(collection_name)
    count = col.count()
    if count == 0:
        return []
    results = col.query(query_texts=[query], n_results=min(n_results, count))
    items = []
    for i, doc in enumerate(results["documents"][0]):
        items.append({
            "text": doc,
            "metadata": results["metadatas"][0][i],
            "id": results["ids"][0][i],
            "distance": results["distances"][0][i] if results.get("distances") else None,
            "collection": collection_name,
        })
    return items

def search_all(query: str, n_results: int = 3) -> list:
    all_results = []
    for col_name in COLLECTIONS:
        results = search(col_name, query, n_results=n_results)
        all_results.extend(results)
    # Sort by distance (lower = more relevant)
    all_results.sort(key=lambda x: x.get("distance") or 999)
    return all_results[:n_results * 2]

def delete(collection_name: str, doc_id: str):
    col = get_collection(collection_name)
    col.delete(ids=[doc_id])

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
    # Sort by timestamp descending
    items.sort(key=lambda x: x["metadata"].get("timestamp", 0), reverse=True)
    return items
