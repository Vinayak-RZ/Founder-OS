from memory.sql_store import (
    get_contacts_needing_followup, get_pipeline_summary,
    get_recent_outreach, get_pending_tasks
)
from memory.vector_store import get_recent as vec_recent
from llm.router import complete
from datetime import datetime
import json

async def daily_briefing() -> str:
    """Generate a comprehensive daily briefing."""
    followups = get_contacts_needing_followup()
    pipeline = get_pipeline_summary()
    recent_outreach = get_recent_outreach(days=7)
    pending_tasks = get_pending_tasks()
    recent_memory = vec_recent("conversations", limit=5)

    data = {
        "date": datetime.now().strftime("%A, %B %d %Y"),
        "followups_due": len(followups),
        "followup_names": [f"{c['name']} @ {c.get('company', '?')}" for c in followups[:5]],
        "pipeline": pipeline,
        "outreach_last_7_days": len(recent_outreach),
        "pending_tasks": len(pending_tasks),
        "top_tasks": [t["title"] for t in pending_tasks[:3]],
    }

    messages = [
        {"role": "system", "content": "You are an executive assistant generating a crisp daily briefing for a startup founder. Use Telegram markdown formatting (* for bold). Be direct and action-oriented."},
        {"role": "user", "content": f"""Generate a daily briefing from this data:
{json.dumps(data, indent=2)}

Format:
- Opening with date and 1 sentence mood/priority
- Follow-ups section (who to contact today)
- Pipeline health (brief)
- Tasks section
- End with one power move recommendation for the day

Use Telegram markdown. Keep it under 400 words."""}
    ]

    return await complete(messages, task_type="analysis")
