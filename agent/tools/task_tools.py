"""Task tools."""
from agent.registry import register
from memory.sql_store import add_task as _add_task, get_pending_tasks, complete_task as _complete_task


@register(
    name="add_task",
    description="Add a to-do/action item for the founder.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "priority": {"type": "integer", "description": "1=high, 2=med, 3=low."},
            "due_at": {"type": "string", "description": "Optional ISO datetime."},
        },
        "required": ["title"],
    },
    category="tasks",
)
async def add_task(title: str, priority: int = 3, due_at: str = None):
    task_id = _add_task(title=title, priority=priority, due_at=due_at)
    return {"task_id": task_id, "title": title}


@register(
    name="list_tasks",
    description="List pending tasks.",
    parameters={"type": "object", "properties": {}},
    category="tasks",
)
async def list_tasks():
    tasks = get_pending_tasks()
    return [
        {"id": t["id"], "title": t["title"], "priority": t["priority"],
         "due_at": t.get("due_at")}
        for t in tasks[:25]
    ]


@register(
    name="complete_task",
    description="Mark a task as done by its id.",
    parameters={
        "type": "object",
        "properties": {"task_id": {"type": "integer"}},
        "required": ["task_id"],
    },
    category="tasks",
)
async def complete_task(task_id: int):
    _complete_task(task_id)
    return {"completed": task_id}
