import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FounderOS/1.0)"}

def scrape_url(url: str, max_chars: int = 3000) -> dict:
    """Scrape a URL and return title + cleaned text."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "lxml")

        # Remove clutter
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title else ""
        text = " ".join(soup.get_text(separator=" ").split())[:max_chars]

        return {"url": url, "title": title, "text": text, "error": None}
    except Exception as e:
        return {"url": url, "title": "", "text": "", "error": str(e)}

def scrape_multiple(urls: list, max_chars_each: int = 2000) -> list:
    return [scrape_url(url, max_chars_each) for url in urls[:5]]
