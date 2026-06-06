"""Self-evolution engine: retrieval + reflection.

- `retrieve_context()` pulls the skills/lessons/goals relevant to the current turn
  so `identity.build_system_prompt` can inject them.
- `reflect()` runs after notable interactions (and nightly): it reviews the turn,
  distills a lesson, and — when warranted — saves a skill or amends the operating
  manual. This is the loop that makes the agent improve itself.
"""
import json
import logging

from agent import store, identity
from memory.vector_store import search as vec_search, add as vec_add
from llm.router import complete

logger = logging.getLogger(__name__)


def _block_from_hits(hits: list) -> str:
    return "\n".join(f"- {h['text'][:300]}" for h in hits)


def retrieve_context(query: str):
    """Return (skills_block, lessons_block, goals_block) for prompt injection."""
    try:
        skills = vec_search("skills", query, n_results=3)
    except Exception:
        skills = []
    try:
        lessons = vec_search("lessons", query, n_results=4)
    except Exception:
        lessons = []
    goals = store.list_goals("active")[:6]
    goals_block = "\n".join(f"- [{g['id']}] {g['title']} ({g.get('detail','')})" for g in goals)
    return _block_from_hits(skills), _block_from_hits(lessons), goals_block


async def reflect(user_message: str, agent_reply: str, tools_used: list = None):
    """Distill a lesson/skill/instruction update from one interaction."""
    tools_used = tools_used or []
    prompt = [
        {"role": "system", "content":
            "You are the reflection module of a self-evolving founder's assistant. "
            "Given one interaction, decide if there is a DURABLE lesson, a reusable "
            "SKILL (playbook), or an operating-manual update worth persisting. "
            "Be selective — most small talk yields nothing. Respond ONLY with JSON."},
        {"role": "user", "content": f"""INTERACTION
User said: {user_message[:1500]}
Tools the agent used: {', '.join(tools_used) or '(none)'}
Agent replied: {agent_reply[:1500]}

Respond ONLY with JSON:
{{
  "lesson": "a durable takeaway phrased as guidance, or empty string",
  "skill": {{"name": "", "when_to_use": "", "steps": ""}},   // all empty if none
  "instruction": {{"section": "How I like to work", "content": ""}}  // content empty if none
}}"""}
    ]
    try:
        raw = await complete(prompt, task_type="analysis", max_tokens=500)
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
    except Exception as e:
        logger.debug(f"[reflect] skipped: {e}")
        return {"reflected": False}

    out = {"reflected": True, "saved": []}

    lesson = (data.get("lesson") or "").strip()
    if lesson:
        store.add_lesson(lesson, situation=user_message[:200], tags="auto_reflection")
        vec_add("lessons", f"{user_message[:200]}\nLesson: {lesson}",
                metadata={"type": "lesson", "tags": "auto_reflection"})
        out["saved"].append("lesson")

    skill = data.get("skill") or {}
    if skill.get("name") and skill.get("steps"):
        store.upsert_skill(skill["name"], skill.get("when_to_use", ""), skill["steps"])
        vec_add("skills", f"{skill['name']}\nWhen: {skill.get('when_to_use','')}\nSteps: {skill['steps']}",
                metadata={"type": "skill", "name": skill["name"]})
        out["saved"].append("skill")

    instr = data.get("instruction") or {}
    if instr.get("content"):
        identity.append_instruction(instr.get("section", "How I like to work"), instr["content"])
        out["saved"].append("instruction")

    return out
