"""Optimizer tools — let the agent run and learn from its own experiments."""
from agent.registry import register
from agent import optimizer


@register(
    name="record_outcome",
    description="Record whether an approach worked, so you learn which strategies win over "
                "time. 'group' is the decision family (e.g. 'email_subject_style', "
                "'followup_timing'); 'variant' is the specific approach you tried.",
    parameters={
        "type": "object",
        "properties": {
            "group": {"type": "string"},
            "variant": {"type": "string"},
            "worked": {"type": "boolean"},
        },
        "required": ["group", "variant", "worked"],
    },
    category="evolution",
)
async def record_outcome(group: str, variant: str, worked: bool):
    optimizer.record(group, variant, worked)
    return {"recorded": True, "leaderboard": optimizer.leaderboard(group)[:5]}


@register(
    name="best_approach",
    description="Ask which approach has worked best for a decision group, based on your "
                "recorded outcomes.",
    parameters={
        "type": "object",
        "properties": {"group": {"type": "string"}},
        "required": ["group"],
    },
    category="evolution",
)
async def best_approach(group: str):
    board = optimizer.leaderboard(group)
    if not board:
        return {"note": f"No experiments recorded yet for '{group}'."}
    return board[:5]
