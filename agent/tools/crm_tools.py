"""CRM / pipeline tools."""
from agent.registry import register
from specialists.crm_agent import (
    add as _add, update_status as _update_status, set_followup as _set_followup,
    get_followups as _get_followups, pipeline as _pipeline, search as _search,
)


@register(
    name="add_contact",
    description="Add a person to the CRM.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "company": {"type": "string"},
            "role": {"type": "string"},
            "email": {"type": "string"},
            "linkedin_url": {"type": "string"},
        },
        "required": ["name"],
    },
    category="crm",
)
async def add_contact(name, company=None, role=None, email=None, linkedin_url=None):
    return await _add(name=name, company=company, role=role, email=email,
                      linkedin_url=linkedin_url, source="agent")


@register(
    name="update_contact_status",
    description="Update a contact's pipeline status (e.g. prospect, contacted, "
                "responded, meeting_set, closed, dead).",
    parameters={
        "type": "object",
        "properties": {
            "contact": {"type": "string", "description": "Name or identifier of the contact."},
            "status": {"type": "string"},
        },
        "required": ["contact", "status"],
    },
    category="crm",
)
async def update_contact_status(contact, status):
    return await _update_status(contact, status)


@register(
    name="set_followup",
    description="Schedule a follow-up for a contact N days from now.",
    parameters={
        "type": "object",
        "properties": {
            "contact": {"type": "string"},
            "days": {"type": "integer"},
        },
        "required": ["contact"],
    },
    category="crm",
)
async def set_followup(contact, days: int = 3):
    return await _set_followup(contact, days=days)


@register(
    name="get_followups",
    description="List contacts whose follow-up is due now.",
    parameters={"type": "object", "properties": {}},
    category="crm",
)
async def get_followups():
    contacts = await _get_followups()
    return [
        {"name": c.get("name"), "company": c.get("company"),
         "status": c.get("status"), "email": c.get("email")}
        for c in contacts[:20]
    ]


@register(
    name="pipeline_status",
    description="Summary of the sales/outreach pipeline by status.",
    parameters={"type": "object", "properties": {}},
    category="crm",
)
async def pipeline_status():
    return await _pipeline()


@register(
    name="search_contacts",
    description="Search CRM contacts by name, company, role, or email.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    category="crm",
)
async def search_contacts(query):
    rows = await _search(query)
    return [
        {"name": r.get("name"), "company": r.get("company"), "role": r.get("role"),
         "email": r.get("email"), "status": r.get("status")}
        for r in rows[:15]
    ]
