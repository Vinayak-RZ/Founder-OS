from memory.sql_store import (
    add_contact, update_contact, get_contact, search_contacts,
    get_contacts_needing_followup, get_pipeline_summary,
    log_outreach, add_task, get_pending_tasks
)
from tools.utils import format_contact
from datetime import datetime, timedelta

async def add(name: str, company: str = None, role: str = None, email: str = None,
              linkedin_url: str = None, source: str = "manual") -> dict:
    contact_id = add_contact(name=name, company=company, role=role,
                             email=email, linkedin_url=linkedin_url, source=source)
    return {"contact_id": contact_id, "message": f"Added {name} to CRM"}

async def update_status(contact_identifier: str, new_status: str) -> dict:
    contacts = search_contacts(contact_identifier)
    if not contacts:
        return {"error": f"No contact found matching '{contact_identifier}'"}
    contact = contacts[0]
    update_contact(contact["id"], status=new_status, updated_at=datetime.now().isoformat())
    return {"message": f"Updated {contact['name']} status to {new_status}"}

async def set_followup(contact_identifier: str, days: int = 3) -> dict:
    contacts = search_contacts(contact_identifier)
    if not contacts:
        return {"error": f"No contact found matching '{contact_identifier}'"}
    contact = contacts[0]
    followup_date = (datetime.now() + timedelta(days=days)).isoformat()
    update_contact(contact["id"], next_followup_at=followup_date)
    return {"message": f"Follow-up set for {contact['name']} in {days} days ({followup_date[:10]})"}

async def get_followups() -> list:
    contacts = get_contacts_needing_followup()
    return contacts

async def pipeline() -> str:
    summary = get_pipeline_summary()
    total = sum(summary.values())
    lines = [f"*Pipeline Summary* ({total} total contacts)", ""]
    status_emoji = {
        "prospect": "🔍", "contacted": "📤", "responded": "💬",
        "meeting_set": "📅", "closed": "✅", "dead": "❌"
    }
    for status, count in sorted(summary.items()):
        emoji = status_emoji.get(status, "•")
        lines.append(f"{emoji} {status.replace('_', ' ').title()}: {count}")
    return "\n".join(lines)

async def search(query: str) -> list:
    return search_contacts(query)

async def log_sent(contact_identifier: str, channel: str, subject: str = None, body: str = None):
    contacts = search_contacts(contact_identifier)
    if not contacts:
        return {"error": "Contact not found"}
    contact = contacts[0]
    log_id = log_outreach(contact["id"], channel=channel, direction="sent", subject=subject, body=body)
    update_contact(contact["id"], last_contacted_at=datetime.now().isoformat(), status="contacted")
    return {"log_id": log_id, "message": f"Logged {channel} outreach to {contact['name']}"}
