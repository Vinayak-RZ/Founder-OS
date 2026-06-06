"""Memory consolidation — the agent's "sleep".

Periodically compresses recent episodic memory (conversations) into durable
semantic memory: key facts, decisions, founder preferences, and open threads.
This fights context bloat and makes long-term recall sharper. Also refreshes the
knowledge graph from the CRM. Meant to be run nightly by the scheduler.
"""
import logging
from datetime import datetime

from memory.vector_store import get_recent, add as vec_add
from memory import graph
from llm.router import complete

logger = logging.getLogger(__name__)


async def consolidate(limit: int = 50) -> dict:
    """Summarize recent conversations into a semantic memory note."""
    recent = get_recent("conversations", limit=limit)
    if len(recent) < 4:
        return {"consolidated": False, "reason": "not enough recent memory"}

    transcript = "\n".join(f"- {r['text'][:300]}" for r in reversed(recent))
    messages = [
        {"role": "system", "content":
            "You are the memory-consolidation module of a founder's assistant. From the "
            "recent interaction log, extract the DURABLE knowledge worth keeping: key "
            "facts, decisions made, the founder's stated preferences, important people/"
            "companies, and open threads to revisit. Drop small talk. Be concise and "
            "factual — bullet points."},
        {"role": "user", "content": f"RECENT INTERACTIONS:\n{transcript}\n\n"
                                     "Write the consolidated memory (<=200 words)."},
    ]
    try:
        summary = await complete(messages, task_type="analysis", max_tokens=400)
    except Exception as e:
        logger.error(f"[consolidation] summary failed: {e}")
        return {"consolidated": False, "reason": str(e)}

    vec_add("notes", f"[Consolidated memory {datetime.now().strftime('%Y-%m-%d')}]\n{summary}",
            metadata={"type": "consolidation", "importance": 2.0})

    # Refresh the knowledge graph from the CRM while we're at it.
    try:
        graph.build_from_crm()
    except Exception as e:
        logger.debug(f"[consolidation] graph refresh failed: {e}")

    return {"consolidated": True, "summary": summary}
