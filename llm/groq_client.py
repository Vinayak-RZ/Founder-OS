from groq import AsyncGroq
from config import config

client = AsyncGroq(api_key=config.groq_api_key)

class RateLimitError(Exception):
    pass

async def complete(messages: list, max_tokens: int = 2048) -> str:
    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        if "rate_limit" in str(e).lower() or "429" in str(e):
            raise RateLimitError(str(e))
        raise
