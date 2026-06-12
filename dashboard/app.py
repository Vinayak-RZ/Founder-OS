"""Founder OS web UI — primary interface for chat, approvals, CRM, memory, and ops.

Run standalone (web-only):
    python -m dashboard.app

Or alongside optional Telegram in main.py when WEB_UI_ENABLED=true.
"""
import logging
import os
import threading

from flask import Flask, send_from_directory

from dashboard.api import bp as api_bp

import agent.tools  # noqa: F401 — register all tools for chat/API

logger = logging.getLogger(__name__)

_STATIC = os.path.join(os.path.dirname(__file__), "static")

app = Flask(__name__, static_folder=_STATIC, static_url_path="/static")
app.register_blueprint(api_bp)

def _behind_proxy() -> bool:
    try:
        from config import config
        return config.behind_proxy
    except Exception:
        return os.getenv("BEHIND_PROXY", "").strip().lower() in ("1", "true", "yes", "on")


if _behind_proxy():
    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)


@app.route("/")
def index():
    return send_from_directory(_STATIC, "index.html")


def start_in_thread(port: int = None, host: str = None):
    """Start the web UI on a daemon thread."""
    from config import config
    port = port or config.dashboard_port
    host = host or os.getenv("WEB_HOST", "127.0.0.1")
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    def _run():
        app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)

    t = threading.Thread(target=_run, daemon=True, name="web-ui")
    t.start()
    logger.info(f"[Web UI] http://{host}:{port}")
    return t


def run_blocking(port: int = None, host: str = None):
    """Run web UI in the foreground (web-only mode)."""
    from config import config
    port = port or config.dashboard_port
    host = host or os.getenv("WEB_HOST", "127.0.0.1")
    logging.getLogger("werkzeug").setLevel(logging.INFO)
    print(f"\n  Founder OS Web UI → http://{host}:{port}\n")
    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    from config import config
    logging.basicConfig(level=logging.INFO)
    run_blocking()
