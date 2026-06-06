"""Social tools. X posting is approval-gated. LinkedIn is draft-only."""
from agent.registry import register
from llm.router import complete
from config import config


@register(
    name="x_post",
    description="Post a tweet to X (Twitter) from the founder's account (<=280 chars). "
                "APPROVAL REQUIRED. Requires the X API to be configured.",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
    requires_approval=True,
    category="social",
)
async def x_post(text: str):
    from integrations import x_client
    return x_client.post(text)


@register(
    name="x_search",
    description="Search recent tweets on X (needs a configured bearer token / paid tier).",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer"},
        },
        "required": ["query"],
    },
    category="social",
)
async def x_search(query: str, max_results: int = 10):
    from integrations import x_client
    return x_client.search(query, max_results=max_results)


@register(
    name="draft_linkedin_post",
    description="Draft a LinkedIn post on a topic. Draft only — LinkedIn does not permit "
                "automated personal posting, so the founder publishes it manually.",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "tone": {"type": "string", "description": "e.g. 'insightful', 'casual', 'bold'."},
        },
        "required": ["topic"],
    },
    category="social",
)
async def draft_linkedin_post(topic: str, tone: str = "insightful"):
    messages = [
        {"role": "system", "content":
            f"You write LinkedIn posts for {config.my_name}, {config.my_role} at "
            f"{config.company_name} ({config.my_one_liner}). Hook in the first line, "
            f"short punchy lines, no hashtag spam, {tone} tone."},
        {"role": "user", "content": f"Write a LinkedIn post about: {topic}. Output only the post."},
    ]
    text = await complete(messages, task_type="general", max_tokens=400)
    return {"draft": text.strip(), "note": "Copy-paste to LinkedIn to publish."}
