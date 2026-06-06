"""AgentCore — the agentic tool-calling loop.

This replaces fixed intent→branch routing. The model is given the full tool
catalog and decides what to call, chaining tools until it can answer. Risky
tools are intercepted and queued for approval. After notable turns, an async
reflection pass lets the agent learn (self-evolution).
"""
import asyncio
import json
import logging

from agent import registry, identity, evolution, approvals
import agent.tools  # noqa: F401 — importing registers every tool
from agent.store import log_action
from llm.tool_client import complete_with_tools
from memory.vector_store import add as vec_add, search_all
from config import config

logger = logging.getLogger(__name__)

MAX_STEPS = 8
HISTORY_TURNS = 8  # how many prior (user/assistant) messages to carry

# Single authorized user → a module-level rolling transcript is fine.
_history = []


def _memory_context(message: str) -> str:
    try:
        hits = search_all(message, n_results=4)
    except Exception:
        return ""
    if not hits:
        return ""
    return "\n".join(f"- [{h['collection']}] {h['text'][:200]}" for h in hits)


async def run(user_message: str, image_context: str = "", actor: str = "user",
              on_status=None) -> str:
    """Process one user turn through the agentic loop and return the reply text."""
    enriched = user_message
    if image_context:
        enriched += f"\n\n[IMAGE CONTENT]\n{image_context}"

    skills_block, lessons_block, goals_block = evolution.retrieve_context(user_message)
    system_prompt = identity.build_system_prompt(
        skills_block=skills_block,
        lessons_block=lessons_block,
        goals_block=goals_block,
        extra_context=_memory_context(user_message),
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(_history[-HISTORY_TURNS:])
    messages.append({"role": "user", "content": enriched})

    schemas = registry.all_schemas()
    tools_used = []
    final_text = ""

    for step in range(MAX_STEPS):
        try:
            resp = await complete_with_tools(messages, schemas)
        except Exception as e:
            logger.error(f"[core] LLM call failed: {e}")
            final_text = f"⚠️ My reasoning engine hit an error: {str(e)[:200]}"
            break

        messages.append(resp["raw"])
        calls = resp.get("tool_calls") or []

        if not calls:
            final_text = (resp.get("content") or "").strip()
            break

        for tc in calls:
            name, args, call_id = tc["name"], tc["arguments"], tc["id"]
            tools_used.append(name)
            tool = registry.get(name)

            if on_status:
                try:
                    await on_status(f"⚙️ {name}…")
                except Exception:
                    pass

            if tool is None:
                result = {"error": f"Unknown tool: {name}"}
            elif tool.requires_approval and not config.auto_approve:
                result = approvals.enqueue(name, args)
            else:
                result = await registry.call(name, args)
                log_action(actor, name, args, json.dumps(result, default=str)[:1500])

            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(result, default=str)[:6000],
            })
    else:
        # Loop exhausted without a final assistant message.
        final_text = final_text or "I did a lot of work but didn't wrap up cleanly. Ask me to continue."

    if not final_text:
        final_text = "Done."

    # Persist the turn and roll history.
    _history.append({"role": "user", "content": enriched})
    _history.append({"role": "assistant", "content": final_text})
    del _history[: max(0, len(_history) - HISTORY_TURNS * 2)]

    try:
        vec_add("conversations", enriched, metadata={"role": "user"})
        vec_add("conversations", final_text, metadata={"role": "assistant"})
    except Exception:
        pass

    # Fire-and-forget self-evolution on substantive turns.
    if tools_used or len(user_message) > 40:
        asyncio.create_task(_safe_reflect(user_message, final_text, tools_used))

    return final_text


async def _safe_reflect(user_message, final_text, tools_used):
    try:
        await evolution.reflect(user_message, final_text, tools_used)
    except Exception as e:
        logger.debug(f"[core] reflection error: {e}")
