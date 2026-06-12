"""Founder OS web UI — primary interface for chat, approvals, CRM, memory, and ops.

Run standalone (web-only):
    python -m dashboard.app

Or alongside optional Telegram in main.py when WEB_UI_ENABLED=true.
"""
import logging
import os
import threading
from datetime import timedelta

from flask import Flask, jsonify, request, send_from_directory

from dashboard.api import bp as api_bp
from dashboard.auth import is_authenticated, path_exempt, pin_required, register_auth_routes

import agent.tools  # noqa: F401 — register all tools for chat/API

logger = logging.getLogger(__name__)

_STATIC = os.path.join(os.path.dirname(__file__), "static")

app = Flask(__name__, static_folder=_STATIC, static_url_path="/static")


def _configure_app(flask_app: Flask) -> None:
    from config import config
    flask_app.config["SECRET_KEY"] = config.flask_secret_key
    flask_app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=14)
    flask_app.config["SESSION_COOKIE_HTTPONLY"] = True
    flask_app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    flask_app.config["SESSION_COOKIE_SECURE"] = config.behind_proxy


_configure_app(app)
app.register_blueprint(api_bp)
register_auth_routes(api_bp)


@app.before_request
def _pin_gate():
    if path_exempt(request.path):
        return None
    if not pin_required() or is_authenticated():
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "unauthorized", "pin_required": True}), 401
    return None

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
