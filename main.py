import asyncio
import logging
import os
import sys
import threading

# Make all output UTF-8 safe so emojis never crash on a Windows cp1252 console.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import config

os.makedirs("./data/logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("./data/logs/founder_os.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def _start_scheduler_async():
    """Run APScheduler on a dedicated asyncio loop (web-only or alongside Telegram)."""
    from scheduler.jobs import start_scheduler

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        start_scheduler(None)
        loop.run_forever()

    t = threading.Thread(target=_run, daemon=True, name="scheduler")
    t.start()
    return t


def _start_telegram():
    from telegram.ext import ApplicationBuilder
    from bot.handlers import register_handlers
    from scheduler.jobs import start_scheduler, set_bot

    logger.info("Telegram channel enabled.")
    app = ApplicationBuilder().token(config.telegram_bot_token).build()
    register_handlers(app)
    set_bot(app)
    start_scheduler(app)
    logger.info("Bot is running on Telegram.")
    app.run_polling(drop_pending_updates=True)


def main():
    logger.info(f"Starting Founder OS for {config.my_name} @ {config.company_name}")

    if config.web_ui_enabled:
        from dashboard.app import start_in_thread, run_blocking
        start_in_thread()
        logger.info(f"Web UI at http://127.0.0.1:{config.dashboard_port}")

    if config.telegram_enabled:
        if not config.web_ui_enabled:
            _start_scheduler_async()
        _start_telegram()
        return

    # Web-only mode: scheduler + blocking web server
    _start_scheduler_async()
    logger.info("Running in web-only mode. Open the Web UI in your browser.")
    from dashboard.app import run_blocking
    run_blocking()


if __name__ == "__main__":
    main()
