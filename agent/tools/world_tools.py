"""World model tools — query the founder's live business snapshot."""
from agent.registry import register
from memory import world_model


@register(
    name="world_state",
    description="Get a structured snapshot of the founder's current business state: CRM "
                "pipeline, active goals, open projects, pending reminders/approvals, "
                "follow-ups due, and today's usage. Use when you need situational awareness.",
    parameters={"type": "object", "properties": {}},
    category="memory",
)
async def world_state():
    return world_model.build_snapshot()
