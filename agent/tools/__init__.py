"""Importing this package registers every tool with the registry.

Order doesn't matter; each module calls registry.register() at import time.
Optional-integration tools (calendar, social) import their heavy deps lazily
inside the tool body, so importing them here never crashes if a lib is missing.
"""
from agent.tools import (  # noqa: F401
    memory_tools,
    crm_tools,
    research_tools,
    task_tools,
    goal_tools,
    reminder_tools,
    outreach_tools,
    calendar_tools,
    social_tools,
    evolution_tools,
)
