"""Outreach tools. Sending is approval-gated."""
from agent.registry import register
from specialists.outreach_agent import draft_email as _draft_email, draft_linkedin_message
from outreach.email_sender import send_email as _send_email
from outreach.tracker import mark_sent


@register(
    name="draft_email",
    description="Draft a personalized cold/outreach email for a contact and/or company. "
                "Returns subject, body, a LinkedIn variant, and the recipient email if known. "
                "This does NOT send — use send_email to send.",
    parameters={
        "type": "object",
        "properties": {
            "contact_name": {"type": "string"},
            "company_name": {"type": "string"},
            "custom_context": {"type": "string", "description": "Anything specific to weave in."},
        },
    },
    category="outreach",
)
async def draft_email(contact_name: str = None, company_name: str = None, custom_context: str = ""):
    return await _draft_email(contact_name=contact_name, company_name=company_name,
                              custom_context=custom_context)


@register(
    name="send_email",
    description="Send an email via the founder's Gmail. APPROVAL REQUIRED. "
                "Provide the final recipient, subject, and body.",
    parameters={
        "type": "object",
        "properties": {
            "to_address": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "contact_name": {"type": "string", "description": "CRM name to log against, if any."},
        },
        "required": ["to_address", "subject", "body"],
    },
    requires_approval=True,
    category="outreach",
)
async def send_email(to_address: str, subject: str, body: str, contact_name: str = None):
    result = _send_email(to_address=to_address, subject=subject, body=body)
    if result.get("success") and contact_name:
        try:
            mark_sent(contact_name, channel="email", subject=subject, body=body)
        except Exception:
            pass
    return result


@register(
    name="draft_linkedin",
    description="Draft a short LinkedIn connection note or DM (<=300 chars). Draft only — "
                "LinkedIn does not allow automated posting, so the founder sends it manually.",
    parameters={
        "type": "object",
        "properties": {
            "contact_name": {"type": "string"},
            "company_name": {"type": "string"},
            "context": {"type": "string"},
        },
        "required": ["contact_name"],
    },
    category="outreach",
)
async def draft_linkedin(contact_name: str, company_name: str = "", context: str = ""):
    note = await draft_linkedin_message(contact_name, company_name=company_name, context=context)
    return {"note": note, "char_count": len(note)}
