"""Free contact / lead discovery utilities.

No paid APIs required. Strategy (all free):
  1. Scrape a company's public pages (home, /contact, /about, /team, ...) and
     pull real emails (incl. mailto links) and phone numbers with regex.
  2. Web search (Serper free tier, or DuckDuckGo fallback) for a person's email.
  3. Generate likely email patterns from name + domain, and validate that the
     domain can actually receive mail via a DNS MX lookup (dnspython).

Scraped emails/phones are HIGH confidence. Pattern-generated emails are a
best guess (marked accordingly) — the standard technique paid tools monetize.
"""
import re
import logging

import requests
from bs4 import BeautifulSoup

from tools.web_search import search

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FounderOS/1.0)"}

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s().\-]{7,}\d)")

# Junk we never want to treat as a real contact email.
_EMAIL_JUNK = ("example.com", "sentry.io", "wixpress.com", "domain.com",
               "email.com", "yourdomain", "@2x", ".png", ".jpg", ".gif",
               ".webp", ".svg")

_CONTACT_PATHS = ["", "/contact", "/contact-us", "/contactus", "/about",
                  "/about-us", "/team", "/our-team", "/people", "/leadership",
                  "/company", "/support"]


def extract_emails(text: str) -> list:
    out = []
    for m in EMAIL_RE.findall(text or ""):
        e = m.strip().strip(".").lower()
        if any(j in e for j in _EMAIL_JUNK):
            continue
        if e not in out:
            out.append(e)
    return out


def extract_phones(text: str) -> list:
    out = []
    for m in PHONE_RE.findall(text or ""):
        digits = re.sub(r"\D", "", m)
        if not (8 <= len(digits) <= 15):
            continue  # filter ids/years/etc.
        clean = m.strip()
        if clean not in out:
            out.append(clean)
    return out


def domain_from_url(url: str) -> str:
    if not url:
        return ""
    url = re.sub(r"^https?://", "", url.strip(), flags=re.IGNORECASE)
    url = url.split("/")[0]
    return url.replace("www.", "").strip().lower()


def find_company_domain(company: str, website: str = "") -> str:
    """Resolve a company's primary domain (prefers a known website)."""
    if website:
        d = domain_from_url(website)
        if d:
            return d
    results = search(f"{company} official website", num_results=3)
    for r in results:
        d = domain_from_url(r.get("url", ""))
        # Skip aggregators / social sites.
        if d and not any(s in d for s in (
                "linkedin.", "facebook.", "twitter.", "x.com", "crunchbase.",
                "wikipedia.", "instagram.", "youtube.", "bloomberg.")):
            return d
    return ""


def scrape_company_contacts(domain: str, max_pages: int = 6) -> dict:
    """Scrape common pages on a domain for emails and phone numbers."""
    if not domain:
        return {"emails": [], "phones": []}

    emails, phones = [], []
    for path in _CONTACT_PATHS[:max_pages + 4]:
        url = f"https://{domain}{path}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=8)
            if r.status_code >= 400:
                continue
            raw_html = r.text  # emails often hide in mailto: links
            for e in extract_emails(raw_html):
                if e not in emails:
                    emails.append(e)
            soup = BeautifulSoup(r.content, "lxml")
            for tag in soup(["script", "style"]):
                tag.decompose()
            text = soup.get_text(separator=" ")
            for p in extract_phones(text):
                if p not in phones:
                    phones.append(p)
        except Exception as e:
            logger.debug(f"contact scrape skip {url}: {e}")
            continue
        if len(emails) >= 8 and len(phones) >= 4:
            break

    return {"emails": emails[:12], "phones": phones[:6]}


def domain_has_mx(domain: str):
    """Return True/False if domain has MX records, or None if unknown."""
    if not domain:
        return None
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, "MX")
        return len(answers) > 0
    except ImportError:
        return None
    except Exception:
        return False


def guess_email_patterns(full_name: str, domain: str) -> list:
    """Generate likely email addresses for a person at a domain."""
    if not full_name or not domain:
        return []
    parts = re.sub(r"[^a-zA-Z\s]", "", full_name).lower().split()
    if len(parts) < 1:
        return []
    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""
    patterns = []
    if last:
        patterns += [
            f"{first}.{last}@{domain}",
            f"{first}{last}@{domain}",
            f"{first[0]}{last}@{domain}",
            f"{first}_{last}@{domain}",
            f"{first[0]}.{last}@{domain}",
            f"{last}.{first}@{domain}",
            f"{first}@{domain}",
        ]
    else:
        patterns += [f"{first}@{domain}"]
    seen = []
    for p in patterns:
        if p not in seen:
            seen.append(p)
    return seen


def find_person_email_via_web(name: str, company: str) -> list:
    """Search the web for a person's email address."""
    emails = []
    for q in (f'"{name}" {company} email', f'{name} {company} contact email'):
        for r in search(q, num_results=3):
            blob = f"{r.get('title','')} {r.get('snippet','')}"
            for e in extract_emails(blob):
                if e not in emails:
                    emails.append(e)
        if emails:
            break
    return emails
