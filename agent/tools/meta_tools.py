"""Meta tools — the agent extending its own capabilities."""
from agent.registry import register
from agent import skills_factory


@register(
    name="create_tool",
    description="Author a NEW tool for yourself when no existing tool fits a recurring need. "
                "Provide a snake_case name, a clear description, a JSON-schema 'parameters' "
                "object, and a non-empty Python function 'body' that uses kwargs and RETURNS a value. "
                "Optionally 'imports' (only json, re, math, datetime, requests, etc. allowed). "
                "APPROVAL REQUIRED: the founder reviews your code before it goes live. Once "
                "approved, the tool persists and is available in future turns.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "snake_case, e.g. 'currency_convert'."},
            "description": {"type": "string"},
            "parameters": {"type": "object", "description": "JSON schema for the tool's args."},
            "body": {"type": "string", "description": "Non-empty Python function body. Use kwargs; must return a value. Do not call this tool if you cannot provide code."},
            "imports": {"type": "string", "description": "Optional import lines (whitelisted modules only)."},
        },
        "required": ["name", "description", "body"],
    },
    requires_approval=True,
    category="meta",
)
def create_tool(name, description, body, parameters=None, imports=""):
    source = skills_factory.build_source(name, description, parameters or {}, body, imports)
    return skills_factory.install_tool(name, source)
