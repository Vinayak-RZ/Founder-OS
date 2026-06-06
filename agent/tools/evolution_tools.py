"""Self-evolution tools — how the agent gets better over time.

These let the agent persist what it learns and even rewrite its own operating
manual. Code self-modification is intentionally proposal-only (approval-gated).
"""
from agent.registry import register
from agent import store, identity
from memory.vector_store import add as vec_add, search as vec_search


@register(
    name="record_lesson",
    description="Persist a lesson you learned (what worked, what failed, a founder "
                "preference, a correction). Lessons are retrieved into future prompts.",
    parameters={
        "type": "object",
        "properties": {
            "lesson": {"type": "string", "description": "The durable takeaway, phrased as guidance."},
            "situation": {"type": "string", "description": "Brief context it came from."},
            "tags": {"type": "string"},
        },
        "required": ["lesson"],
    },
    category="evolution",
)
async def record_lesson(lesson: str, situation: str = "", tags: str = ""):
    lid = store.add_lesson(lesson, situation, tags)
    vec_add("lessons", f"{situation}\nLesson: {lesson}",
            metadata={"type": "lesson", "tags": tags})
    return {"lesson_id": lid, "saved": True}


@register(
    name="save_skill",
    description="Save a reusable playbook (skill) you can follow next time a similar "
                "task appears. Use clear, numbered steps.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "when_to_use": {"type": "string"},
            "steps": {"type": "string", "description": "Numbered, concrete steps."},
        },
        "required": ["name", "when_to_use", "steps"],
    },
    category="evolution",
)
async def save_skill(name: str, when_to_use: str, steps: str):
    sid = store.upsert_skill(name, when_to_use, steps)
    vec_add("skills", f"{name}\nWhen: {when_to_use}\nSteps: {steps}",
            metadata={"type": "skill", "name": name})
    return {"skill_id": sid, "saved": True}


@register(
    name="find_skill",
    description="Search your saved skills/playbooks for one relevant to a task.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    category="evolution",
)
async def find_skill(query: str):
    hits = vec_search("skills", query, n_results=3)
    return [{"text": h["text"][:500]} for h in hits] or {"note": "No saved skills match yet."}


@register(
    name="update_instructions",
    description="Edit your own operating manual (the instructions injected into every "
                "prompt). Use mode='append' to add a bullet under a section, or "
                "mode='replace' to rewrite the whole manual. This is how you durably "
                "change your own behavior.",
    parameters={
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "section": {"type": "string", "description": "Section header for append mode "
                        "(e.g. 'How I like to work')."},
            "mode": {"type": "string", "enum": ["append", "replace"]},
        },
        "required": ["content"],
    },
    category="evolution",
)
async def update_instructions(content: str, section: str = "How I like to work", mode: str = "append"):
    if mode == "replace":
        identity.write_instructions(content)
        return {"updated": True, "mode": "replace"}
    identity.append_instruction(section, content)
    return {"updated": True, "mode": "append", "section": section}


@register(
    name="propose_code_change",
    description="Propose a change to your OWN source code. This NEVER executes — it only "
                "files a proposal for the founder to review and apply by hand. "
                "APPROVAL REQUIRED (and even then, it is recorded, not auto-applied).",
    parameters={
        "type": "object",
        "properties": {
            "file": {"type": "string"},
            "rationale": {"type": "string"},
            "change": {"type": "string", "description": "Describe or paste the proposed change/diff."},
        },
        "required": ["file", "rationale", "change"],
    },
    requires_approval=True,
    category="evolution",
)
async def propose_code_change(file: str, rationale: str, change: str):
    # Recorded only. Applying code is a human action by design.
    vec_add("notes", f"CODE CHANGE PROPOSAL for {file}\nWhy: {rationale}\n{change}",
            metadata={"type": "code_proposal", "file": file})
    return {"recorded": True, "file": file,
            "note": "Proposal saved for human review. Not applied automatically."}
