"""Memory & knowledge tools."""
from agent.registry import register
from memory.vector_store import search_all, add as vec_add, get_recent
from memory.sql_store import add_note


@register(
    name="search_memory",
    description="Semantic search across everything the founder has ever told you "
                "(conversations, research, notes, outreach). Use this to recall context.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to look for."},
            "limit": {"type": "integer", "description": "Max results (default 6)."},
        },
        "required": ["query"],
    },
    category="memory",
)
async def search_memory(query: str, limit: int = 6):
    results = search_all(query, n_results=max(2, limit // 2))
    return [
        {"collection": r["collection"], "text": r["text"][:400]}
        for r in results[:limit]
    ]


@register(
    name="save_memory",
    description="Persist an important fact, note, or piece of knowledge to long-term memory.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The content to remember."},
            "tags": {"type": "string", "description": "Optional comma-separated tags."},
        },
        "required": ["text"],
    },
    category="memory",
)
async def save_memory(text: str, tags: str = ""):
    vec_add("notes", text, metadata={"source": "agent_save", "tags": tags})
    note_id = add_note(content=text, tags=tags)
    return {"saved": True, "note_id": note_id}


@register(
    name="recent_memory",
    description="Get the most recent items from a memory collection "
                "(conversations, research, notes, or outreach).",
    parameters={
        "type": "object",
        "properties": {
            "collection": {"type": "string", "enum": ["conversations", "research", "notes", "outreach"]},
            "limit": {"type": "integer"},
        },
        "required": ["collection"],
    },
    category="memory",
)
async def recent_memory(collection: str, limit: int = 8):
    items = get_recent(collection, limit=limit)
    return [{"text": i["text"][:300]} for i in items]
