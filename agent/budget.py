"""Spend caps, usage counting, and kill switch.

A simple daily LLM-call budget (free to run, protects against runaway loops and
surprise API bills) plus a global pause switch. Counting is centralized so both
the tool-calling client and the plain completion router report into it.
"""
import logging

from agent import store
from config import config

logger = logging.getLogger(__name__)


class BudgetError(Exception):
    pass


def check_before_call():
    """Raise BudgetError if paused or over the daily cap."""
    if config.agent_paused:
        raise BudgetError("Agent is paused (AGENT_PAUSED=true). No model calls allowed.")
    cap = config.daily_llm_call_cap or 0
    if cap > 0:
        used = store.usage_today().get("llm_calls", 0)
        if used >= cap:
            raise BudgetError(f"Daily LLM call cap reached ({used}/{cap}). Resets tomorrow "
                              f"or raise DAILY_LLM_CALL_CAP.")


def note_call():
    try:
        store.incr_usage(llm=1)
    except Exception:
        pass


# Rough per-1K-token USD costs (input, output). Free providers (Groq/Gemini free
# tier) are ~0; OpenAI gpt-4o-mini priced for awareness. Adjust as needed.
MODEL_COSTS = {
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.0025, 0.01),
    "llama-3.3-70b-versatile": (0.0, 0.0),
}


def note_tokens(model: str, prompt_tokens: int, completion_tokens: int):
    inp, out = MODEL_COSTS.get(model, (0.0, 0.0))
    cost = (prompt_tokens / 1000.0) * inp + (completion_tokens / 1000.0) * out
    try:
        store.incr_usage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                         cost_usd=round(cost, 6))
    except Exception:
        pass
    return cost


def status() -> dict:
    u = store.usage_today()
    cap = config.daily_llm_call_cap or 0
    return {
        "day": u.get("day"),
        "llm_calls": u.get("llm_calls", 0),
        "prompt_tokens": u.get("prompt_tokens", 0),
        "completion_tokens": u.get("completion_tokens", 0),
        "est_cost_usd": round(u.get("cost_usd", 0) or 0, 4),
        "cap": cap or "unlimited",
        "paused": config.agent_paused,
        "autonomy_level": config.autonomy_level,
    }
