from memory.vector_store import add as vec_add, search_all
from memory.sql_store import add_note, get_recent_notes
from datetime import datetime

async def save(text: str, source: str = "user", tags: str = "") -> str:
    """Save anything to both vector memory and notes table."""
    doc_id = vec_add("notes", text, metadata={"source": source, "tags": tags, "timestamp": datetime.now().isoformat()})
    note_id = add_note(content=text, tags=tags)
    return f"Saved to memory (vector id: {doc_id}, note id: {note_id})"

async def recall(query: str) -> list:
    """Semantic search across all memory."""
    return search_all(query, n_results=5)

async def get_recent(limit: int = 10) -> list:
    return get_recent_notes(limit=limit)
