"""Production entrypoint — scheduler + Gunicorn (use on EC2 behind nginx)."""
from __future__ import annotations

import os
import sys


def main() -> None:
    from memory.paths import ensure_data_dirs
    from dashboard.startup_checks import run_startup_checks

    ensure_data_dirs()
    run_startup_checks()

    # Background scheduler (heartbeats, backups, reminders)
    from main import _start_scheduler_async

    _start_scheduler_async()

    host = os.getenv("WEB_HOST", "127.0.0.1")
    port = os.getenv("DASHBOARD_PORT", "8787")
    workers = os.getenv("GUNICORN_WORKERS", "2")
    threads = os.getenv("GUNICORN_THREADS", "4")
    timeout = os.getenv("GUNICORN_TIMEOUT", "120")

    # Gunicorn replaces the current process
    os.execvp(
        "gunicorn",
        [
            "gunicorn",
            "dashboard.app:app",
            f"--bind={host}:{port}",
            f"--workers={workers}",
            f"--threads={threads}",
            f"--timeout={timeout}",
            "--access-logfile=-",
            "--error-logfile=-",
            "--capture-output",
        ],
    )


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError:
        print("gunicorn not found — run: pip install gunicorn", file=sys.stderr)
        sys.exit(1)
