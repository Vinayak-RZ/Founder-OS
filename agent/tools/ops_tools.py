"""Operations / maintenance tools: backups and self-care."""
from agent.registry import register
from agent import backup


@register(
    name="backup_now",
    description="Create an immediate backup of the agent's entire memory (SQLite DB + vector "
                "store + world state) into data/backups/. Use before risky changes or on request.",
    parameters={"type": "object", "properties": {}},
    category="meta",
)
def backup_now():
    return backup.create_backup()


@register(
    name="list_backups",
    description="List existing memory backups (newest first) with size and timestamp.",
    parameters={"type": "object", "properties": {}},
    category="meta",
)
def list_backups():
    return backup.list_backups()
