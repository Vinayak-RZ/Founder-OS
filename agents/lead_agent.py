"""Lead-generation agent.

Given a company (and optionally a target role), it:
  1. Researches the company (reuses the research agent) to learn the website
     and key people.
  2. Resolves the company's email domain.
  3. Scrapes the company's public pages for real emails and phone numbers.
  4. For each person, searches the web for their email and generates likely
     email patterns (validated against the domain's MX records).
  5. Saves everyone it finds into the CRM as contacts (source = lead_gen) so
     you can immediately reach out / draft outreach.

Everything here is free — no paid data providers.
"""
import json
import logging

from agents.research_agent import research_company
from memory.sql_store import add_contact, search_contacts
from tools import contact_finder as cf
from tools.web_search import search

logger = logging.getLogger(__name__)


def _coerce_summary(research_result: dict) -> dict:
    summary = research_result.get("summary", {})
    if isinstance(summary, str):
        try:
            summary = json.loads(summary)
        except Exception:
            summary = {}
    return summary or {}


async def find_leads(company: str, role: str = None, max_people: int = 6) -> dict:
    """Discover contactable leads at a company. Returns a structured dict."""
    logger.info(f"[Leads] Finding leads at {company} (role={role})")

    research = await research_company(company)
    summary = _coerce_summary(research)
    website = summary.get("website", "")
    key_people = summary.get("key_people", []) or []

    domain = cf.find_company_domain(company, website=website)
    mx_ok = cf.domain_has_mx(domain) if domain else None

    # Company-wide public contact info.
    generic = cf.scrape_company_contacts(domain) if domain else {"emails": [], "phones": []}

    # If a specific role was requested but research gave us nobody matching,
    # try to discover a name via web search.
    if role:
        matched = [p for p in key_people if role.lower() in (p.get("role", "") or "").lower()]
        if matched:
            key_people = matched
        else:
            for r in search(f"{company} {role} name linkedin", num_results=3):
                title = r.get("title", "")
                # crude name pull: "Jane Doe - Head of X - Company | LinkedIn"
                cand = title.split(" - ")[0].split(" | ")[0].strip()
                if 2 <= len(cand.split()) <= 4 and cand:
                    key_people = [{"name": cand, "role": role,
                                   "linkedin": r.get("url", "")}] + key_people
                    break

    leads = []
    for person in key_people[:max_people]:
        name = (person.get("name") or "").strip()
        if not name or name.lower() in ("", "n/a", "unknown"):
            continue
        prole = person.get("role", "")
        linkedin = person.get("linkedin", "")

        web_emails = cf.find_person_email_via_web(name, company)
        guessed = cf.guess_email_patterns(name, domain) if domain else []

        best_email = web_emails[0] if web_emails else (guessed[0] if guessed else None)
        confidence = "verified (found online)" if web_emails else (
            "best guess" if guessed else "none")

        # Store in CRM (skip exact duplicates by name+company).
        existing = [c for c in search_contacts(name) if (c.get("company") or "").lower() == company.lower()]
        if not existing:
            add_contact(
                name=name,
                company=company,
                role=prole or role,
                email=best_email,
                linkedin_url=linkedin,
                source="lead_gen",
                notes=f"Auto-found lead. Email confidence: {confidence}. "
                      f"Guesses: {', '.join(guessed[:3])}",
            )

        leads.append({
            "name": name,
            "role": prole or role,
            "linkedin": linkedin,
            "email": best_email,
            "email_confidence": confidence,
            "email_guesses": guessed[:4],
            "web_emails": web_emails,
        })

    return {
        "company": company,
        "domain": domain,
        "website": website,
        "domain_accepts_mail": mx_ok,
        "company_emails": generic.get("emails", []),
        "company_phones": generic.get("phones", []),
        "leads": leads,
    }
