import requests
from config import config

def search(query: str, num_results: int = 5) -> list:
    """Search the web with a provider fallback chain.

    Order: Tavily -> Serper -> DuckDuckGo. Whichever is configured and returns
    results first wins. All return a list of {title, url, snippet}.
    """
    if config.tavily_api_key:
        results = _tavily(query, num_results)
        if results:
            return results

    if config.serper_api_key:
        results = _serper(query, num_results)
        if results:
            return results

    return _duckduckgo_fallback(query, num_results)


def _tavily(query: str, num_results: int = 5) -> list:
    """Search via Tavily (AI-native search). Free tier available."""
    try:
        payload = {
            "api_key": config.tavily_api_key,
            "query": query,
            "max_results": num_results,
            "search_depth": "basic",
        }
        response = requests.post("https://api.tavily.com/search", json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()

        results = []
        for r in data.get("results", [])[:num_results]:
            results.append({
                "title": r.get("title"),
                "url": r.get("url"),
                "snippet": r.get("content"),
            })
        return results
    except Exception as e:
        print(f"[Search] Tavily error: {e}, falling back to Serper/DuckDuckGo")
        return []


def _serper(query: str, num_results: int = 5) -> list:
    """Search via Serper.dev (Google results)."""
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
        return []


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
