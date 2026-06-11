"""World templates — facet definitions per venture type (startup, technical, idea).

Founder OS is an aggregator: deep research and coding happen elsewhere. Templates
define which knowledge domains and UI facets matter for each world kind.
"""
from __future__ import annotations

from typing import Optional

# kind (UI) -> template id
KIND_TO_TEMPLATE = {
    "project": "startup",
    "startup": "startup",
    "idea": "idea",
    "research": "research",
    "technical": "technical",
}

WORLD_TEMPLATES: dict[str, dict] = {
    "startup": {
        "label": "Startup / venture",
        "description": "Operating world for a company or venture — industry, market, GTM, leads, product.",
        "facets": [
            {"id": "industry", "label": "Industry analysis", "domain": "vault_industry", "folder": "industry"},
            {"id": "competitors", "label": "Competitor research", "domain": "vault_company", "folder": "company-research"},
            {"id": "market", "label": "Market research", "domain": "vault_industry", "folder": "market"},
            {"id": "gtm", "label": "GTM & marketing", "domain": "vault_product", "folder": "gtm"},
            {"id": "leads", "label": "Leads & pipeline", "domain": "vault_leads", "folder": "leads"},
            {"id": "sales", "label": "Sales & outreach", "domain": "vault_leads", "folder": "sales"},
            {"id": "product", "label": "Product & solution", "domain": "vault_product", "folder": "product-solution"},
            {"id": "clients", "label": "Clients & ICP", "domain": "vault_clients", "folder": "clients"},
        ],
    },
    "technical": {
        "label": "Technical project",
        "description": "Architecture, stack, progress, and trade-offs — implementation lives outside Founder OS.",
        "facets": [
            {"id": "architecture", "label": "Architecture", "domain": "vault_product", "folder": "architecture"},
            {"id": "stack", "label": "Tech stack", "domain": "vault_product", "folder": "tech-stack"},
            {"id": "progress", "label": "Progress log", "domain": "vault_company", "folder": "progress"},
            {"id": "decisions", "label": "Trade-offs & ADRs", "domain": "vault_product", "folder": "decisions"},
            {"id": "docs", "label": "Technical docs", "domain": "vault_company", "folder": "docs"},
        ],
    },
    "idea": {
        "label": "Idea / exploration",
        "description": "Early-stage hypothesis, light research, and next steps.",
        "facets": [
            {"id": "hypothesis", "label": "Hypothesis", "domain": "vault_company", "folder": "hypothesis"},
            {"id": "research", "label": "Research notes", "domain": "vault_industry", "folder": "research"},
            {"id": "next", "label": "Next steps", "domain": "vault_company", "folder": "next-steps"},
        ],
    },
    "research": {
        "label": "Research track",
        "description": "Deep research threads — documents live in the vault; synthesis happens here.",
        "facets": [
            {"id": "papers", "label": "Papers & sources", "domain": "vault_industry", "folder": "sources"},
            {"id": "notes", "label": "Research notes", "domain": "vault_company", "folder": "notes"},
            {"id": "industry", "label": "Industry context", "domain": "vault_industry", "folder": "industry"},
            {"id": "synthesis", "label": "Synthesis", "domain": "vault_product", "folder": "synthesis"},
        ],
    },
}


def template_for_kind(kind: str) -> str:
    return KIND_TO_TEMPLATE.get((kind or "project").lower(), "startup")


def get_template(template_id: str) -> Optional[dict]:
    tid = template_id or "startup"
    t = WORLD_TEMPLATES.get(tid)
    if not t:
        return None
    return {"id": tid, **t}


def facets_for_template(template_id: str) -> list:
    t = get_template(template_id)
    return list(t.get("facets") or []) if t else []


def list_templates() -> list:
    return [{"id": k, "label": v["label"], "description": v.get("description", "")} for k, v in WORLD_TEMPLATES.items()]
