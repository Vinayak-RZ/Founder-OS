import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from specialists.report_agent import daily_briefing
from memory.sql_store import get_contacts_needing_followup
from agent import store

logger = logging.getLogger(__name__)

_bot_app = None
_scheduler = None


def set_bot(app):
    global _bot_app
    _bot_app = app


async def send_to_user(text: str):
    from config import config
    if _bot_app and config.my_telegram_user_id:
        try:
            await _bot_app.bot.send_message(
                chat_id=config.my_telegram_user_id, text=text, parse_mode="Markdown"
            )
        except Exception:
            try:
                await _bot_app.bot.send_message(chat_id=config.my_telegram_user_id, text=text)
            except Exception as e:
                logger.error(f"Scheduled send failed: {e}")


# ── DAILY BRIEFING + FOLLOWUPS (existing) ─────────────────────────────────────

async def job_daily_briefing():
    logger.info("[Scheduler] Daily briefing")
    try:
        briefing = await daily_briefing()
        await send_to_user(f"☀️ *Good morning!*\n\n{briefing}")
    except Exception as e:
        logger.error(f"Daily briefing failed: {e}")


async def job_followup_reminder():
    logger.info("[Scheduler] Follow-up check")
    try:
        contacts = get_contacts_needing_followup()
        if contacts:
            lines = [f"🔔 *{len(contacts)} follow-up(s) due today:*", ""]
            for c in contacts[:5]:
                lines.append(f"• {c['name']} @ {c.get('company', '?')} (status: {c.get('status', '?')})")
            await send_to_user("\n".join(lines))
    except Exception as e:
        logger.error(f"Follow-up reminder failed: {e}")


# ── REMINDERS ─────────────────────────────────────────────────────────────────

def _next_occurrence(due_iso: str, repeat: str) -> str:
    base = datetime.fromisoformat(due_iso)
    delta = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1),
             "monthly": timedelta(days=30)}.get(repeat, timedelta(days=1))
    nxt = base + delta
    while nxt <= datetime.now():
        nxt += delta
    return nxt.isoformat()


async def job_fire_reminder(reminder_id: int):
    reminders = {r["id"]: r for r in store.get_pending_reminders()}
    r = reminders.get(reminder_id)
    if not r:
        return
    await send_to_user(f"⏰ *Reminder:* {r['text']}")
    if r.get("repeat"):
        nxt = _next_occurrence(r["due_at"], r["repeat"])
        store.reschedule_reminder(reminder_id, nxt)
        schedule_reminder(reminder_id, nxt)
    else:
        store.set_reminder_status(reminder_id, "done")


def schedule_reminder(reminder_id: int, due_at_iso: str):
    """Schedule (or reschedule) a one-off reminder job on the live scheduler."""
    if _scheduler is None:
        return  # will be picked up by load_pending_reminders on next start
    try:
        run_date = datetime.fromisoformat(due_at_iso)
    except Exception:
        run_date = datetime.now() + timedelta(minutes=1)
    if run_date <= datetime.now():
        run_date = datetime.now() + timedelta(seconds=5)
    _scheduler.add_job(
        job_fire_reminder, DateTrigger(run_date=run_date),
        args=[reminder_id], id=f"reminder_{reminder_id}",
        replace_existing=True, misfire_grace_time=3600,
    )


def cancel_reminder_job(reminder_id: int):
    if _scheduler is None:
        return
    try:
        _scheduler.remove_job(f"reminder_{reminder_id}")
    except Exception:
        pass


def load_pending_reminders():
    for r in store.get_pending_reminders():
        schedule_reminder(r["id"], r["due_at"])


# ── HEARTBEAT (proactivity) ───────────────────────────────────────────────────

async def job_heartbeat():
    logger.info("[Scheduler] Heartbeat")
    from agent import core
    prompt = (
        "[HEARTBEAT] This is an autonomous self-check, not a user message. Review my "
        "active goals, any follow-ups due, pending reminders, and pipeline. If there is "
        "something genuinely useful to do or flag right now, do it (use tools) or propose "
        "it, then give me a 2-4 line update. If nothing needs my attention, reply with "
        "exactly the single word: NOTHING."
    )
    try:
        reply = await core.run(prompt, actor="heartbeat")
        if reply and reply.strip().upper() != "NOTHING":
            await send_to_user(f"🛰 *Proactive update*\n\n{reply}")
    except Exception as e:
        logger.error(f"Heartbeat failed: {e}")


# ── START ─────────────────────────────────────────────────────────────────────

def start_scheduler(app) -> AsyncIOScheduler:
    global _scheduler
    from config import config
    set_bot(app)
    _scheduler = AsyncIOScheduler()

    _scheduler.add_job(job_daily_briefing, CronTrigger(hour=8, minute=0), id="daily_briefing")
    _scheduler.add_job(job_followup_reminder, CronTrigger(hour=10, minute=0), id="followup_reminder")

    hours = max(1, int(getattr(config, "heartbeat_hours", 4) or 4))
    _scheduler.add_job(
        job_heartbeat, CronTrigger(hour=f"9-21/{hours}", minute=0), id="heartbeat"
    )

    _scheduler.start()
    load_pending_reminders()
    logger.info(f"[Scheduler] Started. Briefing 08:00, follow-ups 10:00, heartbeat every {hours}h (9-21).")
    return _scheduler
