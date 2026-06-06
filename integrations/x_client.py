"""X (Twitter) integration via tweepy.

NOTE on feasibility: posting works on the official X API, but meaningful access
is paid (the free tier is tightly capped). Reading/search is heavily rate-limited
on lower tiers. tweepy is imported lazily so the bot runs without it installed.
"""
from config import config


def is_configured() -> bool:
    return bool(config.x_api_key and config.x_api_secret
                and config.x_access_token and config.x_access_token_secret)


def _client():
    import tweepy
    return tweepy.Client(
        consumer_key=config.x_api_key,
        consumer_secret=config.x_api_secret,
        access_token=config.x_access_token,
        access_token_secret=config.x_access_token_secret,
        bearer_token=config.x_bearer_token or None,
    )


def post(text: str) -> dict:
    if not is_configured():
        return {"error": "X API not configured. Set X_API_* keys in .env."}
    if len(text) > 280:
        return {"error": f"Tweet too long ({len(text)} chars, max 280)."}
    resp = _client().create_tweet(text=text)
    data = getattr(resp, "data", {}) or {}
    tid = data.get("id")
    return {"posted": True, "id": tid, "url": f"https://x.com/i/web/status/{tid}" if tid else None}


def search(query: str, max_results: int = 10) -> list:
    if not config.x_bearer_token:
        return [{"error": "X search needs X_BEARER_TOKEN (and a paid tier for useful access)."}]
    import tweepy
    client = tweepy.Client(bearer_token=config.x_bearer_token)
    resp = client.search_recent_tweets(query=query, max_results=min(max(max_results, 10), 100))
    return [{"id": t.id, "text": t.text} for t in (resp.data or [])]
