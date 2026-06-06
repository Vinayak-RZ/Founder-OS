"""Reminder tools.

Reminders are persisted in SQLite and scheduled on APScheduler. The agent should
pass an absolute ISO datetime in `due_at_iso` (it knows the current time from the
system prompt). As a convenience, `minutes_from_now` is also accepted.
"""
import re
from datetime import datetime, timedelta

from agent.registry import register
from agent import store


def _resolve_due(due_at_iso: str = None, minutes_from_now: int = None) -> str:
    if minutes_from_now is not None:
        return (datetime.now() + timedelta(minutes=int(minutes_from_now))).isoformat()
    if due_at_iso:
        s = due_at_iso.strip().replace("Z", "")
        try:
            return datetime.fromisoformat(s).isoformat()
        except Exception:
            # Loose fallback: pull the first datetime-ish token.
            m = re.search(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}", s)
            if m:
                return datetime.fromisoformat(m.group(0).replace(" ", "T")).isoformat()
    # Default: one hour out.
    return (datetime.now() + timedelta(hours=1)).isoformat()


@register(
    name="set_reminder",
    description="Set a reminder. The founder will be pinged on Telegram at the due "
                "time. Pass an absolute ISO datetime in due_at_iso (compute it from "
                "the current time given in your prompt), or minutes_from_now. Optional "
                "repeat: 'daily', 'weekly', or 'monthly'.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "What to remind about."},
            "due_at_iso": {"type": "string", "description": "Absolute ISO datetime."},
            "minutes_from_now": {"type": "integer"},
            "repeat": {"type": "string", "enum": ["daily", "weekly", "monthly"]},
        },
        "required": ["text"],
    },
    category="reminders",
)
async def set_reminder(text: str, due_at_iso: str = None, minutes_from_now: int = None,
                       repeat: str = None):
    due = _resolve_due(due_at_iso, minutes_from_now)
    rid = store.add_reminder(text, due, repeat)
    # Schedule it on the live scheduler (lazy import avoids a circular import).
    try:
        from scheduler.jobs import schedule_reminder
        schedule_reminder(rid, due)
    except Exception as e:
        return {"reminder_id": rid, "due_at": due, "scheduled": False, "note": str(e)}
    return {"reminder_id": rid, "due_at": due, "repeat": repeat, "scheduled": True}


@register(
    name="list_reminders",
    description="List pending reminders.",
    parameters={"type": "object", "properties": {}},
    category="reminders",
)
async def list_reminders():
    return [
        {"id": r["id"], "text": r["text"], "due_at": r["due_at"], "repeat": r.get("repeat")}
        for r in store.get_pending_reminders()
    ]


@register(
    name="cancel_reminder",
    description="Cancel a pending reminder by id.",
    parameters={
        "type": "object",
        "properties": {"reminder_id": {"type": "integer"}},
        "required": ["reminder_id"],
    },
    category="reminders",
)
async def cancel_reminder(reminder_id: int):
    store.set_reminder_status(reminder_id, "cancelled")
    try:
        from scheduler.jobs import cancel_reminder_job
        cancel_reminder_job(reminder_id)
    except Exception:
        pass
    return {"cancelled": reminder_id}
