"""Specialist sub-agents — aggregator-focused delegation.

The supervisor routes focused work to specialists. Each specialist queries CRM,
vault, and status tools — it does not replace deep research (Cursor) or coding repos.
"""
import asyncio
import logging

from agent import registry
from agent.loop import execute_loop
from config import config

logger = logging.getLogger(__name__)

# Aggregator-oriented specialists (max 5). Outreach stays core; others coordinate intel.
SPECIALISTS = {
    "pulse": {
        "label": "Pulse",
        "role": "aggregator",
        "skills": [],
        "categories": {"tasks", "reminders", "crm", "goals", "meta"},
        "brief": "Operating pulse across all parallel projects. Summarize what's happening: "
                 "open tasks, CRM follow-ups, goals, approvals, and linked vault activity. "
                 "Surface status and gaps — do not run deep research or write code.",
    },
    "outreach": {
        "label": "Outreach",
        "role": "outreach",
        "skills": ["lead-generation"],
        "categories": {"outreach", "crm"},
        "brief": "Outreach specialist — draft sharp, personalized messages and manage CRM "
                 "pipeline. Sending stays approval-gated. Primary use case for Founder OS.",
    },
    "leads": {
        "label": "Leads",
        "role": "leads",
        "skills": ["lead-generation"],
        "categories": {"crm", "outreach", "research"},
        "brief": "Lead generation coordinator — organize prospects from CRM and the knowledge "
                 "vault, suggest who to contact next, and draft outreach. Lists and CRM updates "
                 "only; deep prospecting happens in external tools.",
    },
    "market": {
        "label": "Market intel",
        "role": "research",
        "skills": ["industry-analysis"],
        "categories": {"research", "memory"},
        "brief": "Market and industry intelligence — query the knowledge vault and graph for "
                 "industry analysis, competitors, and industrial context. Summarize and compare; "
                 "do not invent data. New deep research is done outside Founder OS.",
    },
    "vault": {
        "label": "Vault",
        "role": "knowledge",
        "skills": ["industry-analysis"],
        "categories": {"research", "memory"},
        "brief": "Knowledge vault librarian — search across all linked project documentation "
                 "(per-world domains: company, leads, industry, product, clients). Answer "
                 "grounded questions with citations. Ingest and link repos when asked.",
    },
}


def list_specialists() -> list:
    return list(SPECIALISTS.keys())


def specialist_meta(name: str) -> dict:
    spec = SPECIALISTS.get(name) or {}
    return {
        "id": name,
        "label": spec.get("label", name.title()),
        "role": spec.get("role", "specialist"),
        "skills": spec.get("skills") or [],
        "brief": spec.get("brief", ""),
        "categories": sorted(spec.get("categories") or []),
    }


async def run_subagent(name: str, task: str, actor: str = "subagent", on_status=None,
                       world_id: str | None = None, should_cancel=None) -> dict:
    spec = SPECIALISTS.get(name)
    if not spec:
        return {"error": f"Unknown specialist '{name}'. Options: {list_specialists()}"}

    from memory import worlds as hierarchical_worlds
    world_block = ""
    try:
        world_block = hierarchical_worlds.snapshot_block(world_id, max_chars=1400)
    except Exception:
        pass
    system = (
        f"{spec['brief']}\n\n"
        f"You are a delegated sub-agent for {config.my_name} at {config.company_name}. "
        f"Founder OS aggregates parallel work — query vault/CRM/status, return concise "
        f"actionable summaries for the supervisor. Do not chit-chat."
    )
    if spec.get("skills"):
        system += f"\nRelevant skills: {', '.join(spec['skills'])}."
    if world_block:
        system += f"\n\n[ACTIVE WORLD CONTEXT]\n{world_block}"
    schemas = registry.schemas_for(spec["categories"])
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": task}]
    tools_used = []
    result = await execute_loop(messages, schemas, actor=f"subagent:{name}",
                                on_status=on_status, tools_used=tools_used, max_steps=6,
                                should_cancel=should_cancel)
    return {"specialist": name, "result": result, "tools_used": tools_used}


async def run_parallel(tasks: list) -> list:
    """Run several {specialist, task} handoffs concurrently."""
    coros = [run_subagent(t.get("specialist", ""), t.get("task", "")) for t in tasks]
    return await asyncio.gather(*coros, return_exceptions=False)
