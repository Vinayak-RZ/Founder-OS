import json
from tools.web_search import search
from tools.scraper import scrape_url
from memory.vector_store import add as mem_add
from memory.sql_store import add_company, search_companies
from llm.router import complete

async def research_company(company_name: str) -> dict:
    """Full research pipeline for a company."""
    print(f"[Research] Starting research for: {company_name}")

    # Check if already researched
    existing = search_companies(company_name)
    if existing:
        return {"status": "cached", "company": existing[0], "summary": existing[0].get("research_summary", "")}

    # Step 1: Web searches
    overview_results = search(f"{company_name} company overview site:linkedin.com OR crunchbase.com OR {company_name}.com", num_results=5)
    leadership_results = search(f"{company_name} CEO founder leadership team", num_results=3)
    news_results = search(f"{company_name} news 2024 2025", num_results=3)

    # Step 2: Scrape top result
    scraped = {}
    if overview_results:
        scraped = scrape_url(overview_results[0]["url"])

    # Step 3: Build raw context
    raw = f"""
Company: {company_name}

SEARCH RESULTS (Overview):
{json.dumps(overview_results, indent=2)}

SEARCH RESULTS (Leadership):
{json.dumps(leadership_results, indent=2)}

SEARCH RESULTS (Recent News):
{json.dumps(news_results, indent=2)}

SCRAPED WEBSITE:
Title: {scraped.get('title', '')}
Content: {scraped.get('text', '')[:2000]}
"""

    # Step 4: LLM summary
    messages = [
        {"role": "system", "content": "You are a business research assistant. Extract and structure company information concisely."},
        {"role": "user", "content": f"""Based on this raw research data, produce a structured summary for: {company_name}

{raw}

Respond in this exact JSON format:
{{
  "name": "",
  "website": "",
  "industry": "",
  "size": "",
  "location": "",
  "what_they_do": "",
  "key_people": [
    {{"name": "", "role": "", "linkedin": ""}}
  ],
  "recent_news": "",
  "icp_score": 5,
  "icp_reasoning": "",
  "outreach_angle": ""
}}
Only output JSON, nothing else."""}
    ]

    raw_response = await complete(messages, task_type="research")

    try:
        # Strip any markdown fences
        clean = raw_response.strip().replace("```json", "").replace("```", "").strip()
        summary = json.loads(clean)
    except Exception:
        summary = {"name": company_name, "what_they_do": raw_response[:500], "error": "parse_failed"}

    # Save to SQL
    company_id = add_company(
        name=company_name,
        website=summary.get("website"),
        industry=summary.get("industry"),
        size=summary.get("size"),
        location=summary.get("location"),
        description=summary.get("what_they_do"),
        research_summary=json.dumps(summary),
        icp_score=summary.get("icp_score"),
    )

    # Save to vector memory
    mem_add("research", json.dumps(summary), metadata={"company": company_name, "type": "company_research"})

    return {"status": "new", "company_id": company_id, "summary": summary}
