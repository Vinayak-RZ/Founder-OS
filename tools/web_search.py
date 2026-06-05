import requests
from config import config

def search(query: str, num_results: int = 5) -> list:
    """Search the web using Serper.dev and return structured results."""
    if not config.serper_api_key:
        return _duckduckgo_fallback(query, num_results)

    headers = {"X-API-KEY": config.serper_api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": num_results}

    try:
        response = requests.post("https://google.serper.dev/search", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []
        for r in data.get("organic", [])[:num_results]:
            results.append({
                "title": r.get("title"),
                "url": r.get("link"),
                "snippet": r.get("snippet"),
            })
        return results
    except Exception as e:
        print(f"[Search] Serper error: {e}, falling back to DuckDuckGo")
        return _duckduckgo_fallback(query, num_results)

def _duckduckgo_fallback(query: str, num_results: int = 5) -> list:
    """Free fallback using DuckDuckGo instant answer API."""
    try:
        params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        r = requests.get("https://api.duckduckgo.com/", params=params, timeout=10)
        data = r.json()
        results = []
        if data.get("AbstractText"):
            results.append({"title": data.get("Heading", query), "url": data.get("AbstractURL", ""), "snippet": data.get("AbstractText", "")})
        for topic in data.get("RelatedTopics", [])[:num_results - 1]:
            if "Text" in topic:
                results.append({"title": topic.get("Text", "")[:60], "url": topic.get("FirstURL", ""), "snippet": topic.get("Text", "")})
        return results[:num_results]
    except Exception:
        return []
