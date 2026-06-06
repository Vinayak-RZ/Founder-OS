"""Google Calendar tools. Deleting events is approval-gated."""
from agent.registry import register


def _not_connected_msg():
    return {
        "error": "Google Calendar is not connected yet.",
        "how_to_fix": "Run `python scripts/google_auth.py` once to authorize, then retry.",
    }


@register(
    name="calendar_create_event",
    description="Create an event on the founder's primary Google Calendar. "
                "Pass ISO datetimes (compute from the current time in your prompt).",
    parameters={
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "start_iso": {"type": "string"},
            "end_iso": {"type": "string"},
            "description": {"type": "string"},
            "location": {"type": "string"},
            "attendees": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["summary", "start_iso"],
    },
    category="calendar",
)
async def calendar_create_event(summary, start_iso, end_iso=None, description="",
                                location="", attendees=None):
    from integrations import google_calendar as gc
    if not gc.is_configured():
        return _not_connected_msg()
    return gc.create_event(summary, start_iso, end_iso, description, location, attendees)


@register(
    name="calendar_list_events",
    description="List upcoming events on the founder's primary Google Calendar.",
    parameters={
        "type": "object",
        "properties": {
            "max_results": {"type": "integer"},
            "time_min_iso": {"type": "string"},
        },
    },
    category="calendar",
)
async def calendar_list_events(max_results: int = 10, time_min_iso: str = None):
    from integrations import google_calendar as gc
    if not gc.is_configured():
        return _not_connected_msg()
    return gc.list_events(max_results=max_results, time_min_iso=time_min_iso)


@register(
    name="calendar_delete_event",
    description="Delete a calendar event by id. APPROVAL REQUIRED.",
    parameters={
        "type": "object",
        "properties": {"event_id": {"type": "string"}},
        "required": ["event_id"],
    },
    requires_approval=True,
    category="calendar",
)
async def calendar_delete_event(event_id: str):
    from integrations import google_calendar as gc
    if not gc.is_configured():
        return _not_connected_msg()
    return gc.delete_event(event_id)
