"""AgentCore — the agentic loop (plan -> execute -> verify).

The model is given the full tool catalog and decides what to call, chaining tools
until it can answer. For non-trivial goals it first drafts an explicit plan
(plan-and-execute), and before finalizing it self-verifies the answer
(Reflexion / chain-of-verification). Risky tools are intercepted for approval.
After notable turns an async reflection pass lets the agent learn.
"""
import asyncio
import json
import logging

from agent import registry, identity, evolution, planner, critic, trace, tool_retrieval, confidence
from agent.loop import execute_loop
import agent.tools  # noqa: F401 — importing registers every tool
from agent.store import set_plan_status
from memory.vector_store import add as vec_add, search_all
from memory import worlds as hierarchical_worlds
from config import config

logger = logging.getLogger(__name__)

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


async def _rag_context(message: str, mode: str, world_id: str | None) -> str:
    """Prefetch retrieval context based on user-selected RAG mode."""
    mode = (mode or "auto").strip().lower()
    if mode in ("", "auto"):
        return _memory_context(message)
    try:
        if mode == "hybrid":
            from memory.retrieval import hybrid_search
            hits = hybrid_search(message, k=8)
            if not hits:
                return ""
            lines = [f"- [{h.get('collection', '?')}] {h['text'][:240]}" for h in hits]
            return "[HYBRID RAG — dense + BM25]\n" + "\n".join(lines)

        if mode == "documents":
            from memory.retrieval import hybrid_search
            hits = hybrid_search(message, collections=["documents"], k=8)
            if not hits:
                return ""
            lines = [f"- {h['text'][:260]}" for h in hits]
            return "[DOCUMENT RAG]\n" + "\n".join(lines)

        if mode == "graphrag":
            from memory import graphrag
            answer = await graphrag.global_answer(message, top_n=4)
            if answer:
                return f"[GRAPH RAG — network-level context]\n{answer[:3500]}"
            return ""

        if mode == "vault":
            from memory import knowledge_vault
            wid = world_id if world_id and world_id != "root" else None
            hits = knowledge_vault.search_vault(message, world_id=wid, n_results=8)
            if not hits:
                return "[VAULT] No vault hits — link docs in Worlds or pick a sub-world."
            lines = [
                f"- [{h.get('metadata', {}).get('domain', '?')}] "
                f"{h.get('metadata', {}).get('source', '')}: {h['text'][:220]}"
                for h in hits
            ]
            return "[KNOWLEDGE VAULT RAG]\n" + "\n".join(lines)
    except Exception as e:
        logger.debug(f"[core] rag mode {mode} failed: {e}")
    return _memory_context(message)


async def run(user_message: str, image_context: str = "", actor: str = "user",
              on_status=None, world_id: str | None = None, rag_mode: str = "auto",
              should_cancel=None) -> str:
    """Process one user turn through plan -> execute -> verify and return the reply."""
    if config.agent_paused:
        return "⏸ I'm paused right now (AGENT_PAUSED is on). Turn it off to let me act again."
    if should_cancel and should_cancel():
        return "⏹ Stopped by user."

    trace.start(actor, user_message)
    enriched = user_message
    if image_context:
        enriched += f"\n\n[IMAGE CONTENT]\n{image_context}"

    mem_ctx = await _rag_context(user_message, rag_mode, world_id)
    try:
        world_ctx = hierarchical_worlds.snapshot_block(world_id)
    except Exception:
        world_ctx = ""
    extra = "\n\n".join(x for x in [world_ctx, mem_ctx] if x)

    skills_block, lessons_block, goals_block = evolution.retrieve_context(user_message)
    system_prompt = identity.build_system_prompt(
        skills_block=skills_block,
        lessons_block=lessons_block,
        goals_block=goals_block,
        extra_context=extra,
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(_history[-HISTORY_TURNS:])

    # ── PLAN (only for non-trivial goals) ─────────────────────────────────────
    plan_id = None
    deliberate = planner.needs_planning(user_message)
    if deliberate:
        if on_status:
            try:
                await on_status("🧭 planning…")
            except Exception:
                pass
        try:
            plan = await planner.make_plan(user_message, context=goals_block)
            plan_id = plan.get("plan_id")
            rendered = planner.render_plan(plan)
            if rendered:
                trace.add("plan", {"plan_id": plan_id, "steps": len(plan.get("steps") or [])})
                messages.append({"role": "system",
                                 "content": "WORKING PLAN (follow it, adapt if needed):\n" + rendered})
        except Exception as e:
            logger.debug(f"[core] planning skipped: {e}")

    messages.append({"role": "user", "content": enriched})

    # Tool-RAG: a direct user turn only sees the tools relevant to it (+ a core
    # set). Proactive/system actors (heartbeat, sub-agents) keep the full catalog
    # so autonomous routines never lose a capability.
    if actor == "user":
        schemas = tool_retrieval.schemas_for_message(user_message)
    else:
        schemas = registry.all_schemas()
    tools_used = []

    # ── EXECUTE ────────────────────────────────────────────────────────────────
    final_text = await execute_loop(messages, schemas, actor, on_status, tools_used,
                                    should_cancel=should_cancel)

    if should_cancel and should_cancel():
        trace.finish("⏹ Stopped by user.")
        return "⏹ Stopped by user."

    # ── VERIFY + one refinement (only for deliberate turns) ────────────────────
    if deliberate and final_text and not final_text.startswith("⚠️"):
        try:
            check = await critic.verify_answer(
                user_message, final_text, work_summary=", ".join(tools_used))
            if not check.get("ok", True) and check.get("suggestion"):
                if on_status:
                    try:
                        await on_status("🔍 self-checking…")
                    except Exception:
                        pass
                messages.append({"role": "assistant", "content": final_text})
                messages.append({"role": "user", "content":
                                 f"[SELF-CHECK] Problem found: {check.get('issues','')}. "
                                 f"{check.get('suggestion','')} Now give me the corrected final reply."})
                final_text = await execute_loop(messages, schemas, actor, on_status,
                                                tools_used, max_steps=3)
            # Abstention: surface genuinely low-confidence answers honestly.
            final_text = confidence.annotate(
                final_text, check.get("confidence", "high"), check.get("clarify", ""))
        except Exception as e:
            logger.debug(f"[core] verify skipped: {e}")

    if not final_text:
        final_text = "Done."

    if plan_id:
        try:
            set_plan_status(plan_id, "done")
        except Exception:
            pass

    trace.finish(final_text)

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
