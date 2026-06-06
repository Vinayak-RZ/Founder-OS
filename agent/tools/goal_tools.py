"""Goal tools — long-running objectives the agent works toward proactively."""
from agent.registry import register
from agent import store


@register(
    name="add_goal",
    description="Record a long-running objective the founder wants pursued over time "
                "(e.g. 'book 5 demos with insurtech CTOs this month'). The heartbeat "
                "will revisit active goals and propose progress.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "detail": {"type": "string"},
            "priority": {"type": "integer"},
        },
        "required": ["title"],
    },
    category="goals",
)
async def add_goal(title: str, detail: str = "", priority: int = 3):
    gid = store.add_goal(title, detail, priority)
    return {"goal_id": gid, "title": title}


@register(
    name="list_goals",
    description="List goals. status can be 'active', 'done', 'paused', 'dropped', or 'all'.",
    parameters={
        "type": "object",
        "properties": {"status": {"type": "string"}},
    },
    category="goals",
)
async def list_goals(status: str = "active"):
    return store.list_goals(status)


@register(
    name="update_goal",
    description="Update a goal's status, detail, or priority.",
    parameters={
        "type": "object",
        "properties": {
            "goal_id": {"type": "integer"},
            "status": {"type": "string"},
            "detail": {"type": "string"},
            "priority": {"type": "integer"},
        },
        "required": ["goal_id"],
    },
    category="goals",
)
async def update_goal(goal_id: int, status: str = None, detail: str = None, priority: int = None):
    kwargs = {k: v for k, v in
              {"status": status, "detail": detail, "priority": priority}.items()
              if v is not None}
    store.update_goal(goal_id, **kwargs)
    return {"updated": goal_id, "changes": kwargs}
