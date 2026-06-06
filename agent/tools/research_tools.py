"""Research & web tools."""
from agent.registry import register
from specialists.research_agent import research_company as _research_company
from specialists.lead_agent import find_leads as _find_leads
from tools.web_search import search as _web_search
from tools.scraper import scrape_url as _scrape_url


@register(
    name="research_company",
    description="Run the full research pipeline on a company (web search + scrape + "
                "AI summary). Caches results in the CRM. Returns a structured summary.",
    parameters={
        "type": "object",
        "properties": {"company_name": {"type": "string"}},
        "required": ["company_name"],
    },
    category="research",
)
async def research_company(company_name: str):
    result = await _research_company(company_name)
    return result.get("summary", result)


@register(
    name="web_search",
    description="Search the web and return a list of {title, url, snippet}.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "num_results": {"type": "integer"},
        },
        "required": ["query"],
    },
    category="research",
)
async def web_search(query: str, num_results: int = 5):
    return _web_search(query, num_results=num_results)


@register(
    name="scrape_url",
    description="Fetch and read a web page; returns its title and cleaned text.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "max_chars": {"type": "integer"},
        },
        "required": ["url"],
    },
    category="research",
)
async def scrape_url(url: str, max_chars: int = 4000):
    return _scrape_url(url, max_chars=max_chars)


@register(
    name="find_leads",
    description="Find contactable leads (emails/phones/LinkedIn) for a company, a "
                "role at a company, or specific named people. Saves them to the CRM.",
    parameters={
        "type": "object",
        "properties": {
            "company": {"type": "string"},
            "role": {"type": "string", "description": "Target role, e.g. 'head of sales'."},
            "people": {"type": "array", "items": {"type": "string"},
                       "description": "Explicit names to find."},
        },
    },
    category="research",
)
async def find_leads(company: str = None, role: str = None, people: list = None):
    return await _find_leads(company=company, role=role, people=people or [])
