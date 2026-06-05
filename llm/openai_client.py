from openai import AsyncOpenAI
from config import config

client = AsyncOpenAI(api_key=config.openai_api_key)

async def complete(messages: list, max_tokens: int = 2048) -> str:
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content
