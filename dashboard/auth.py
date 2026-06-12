"""6-digit PIN gate for the web UI — set DASHBOARD_PIN in .env to enable."""
from __future__ import annotations

import hmac
import re
import time
from typing import Optional

from flask import jsonify, session

_PIN_RE = re.compile(r"^\d{6}$")
_MAX_ATTEMPTS = 8
_LOCKOUT_SECONDS = 300
_failures: dict[str, tuple[int, float]] = {}


def pin_required() -> bool:
    from config import config
    pin = (config.dashboard_pin or "").strip()
    return bool(pin and _PIN_RE.match(pin))


def is_authenticated() -> bool:
    if not pin_required():
        return True
    return session.get("fos_auth") is True


def path_exempt(path: str) -> bool:
    if path.startswith("/static/"):
        return True
    if path in ("/", "/favicon.ico"):
        return True
    if path in ("/api/auth/status", "/api/auth/pin", "/api/health", "/api/github/callback"):
        return True
    return False


def _client_ip() -> str:
    from flask import request
    return (request.headers.get("X-Forwarded-For") or request.remote_addr or "unknown").split(",")[0].strip()


def _rate_limited() -> Optional[int]:
    ip = _client_ip()
    entry = _failures.get(ip)
    if not entry:
        return None
    count, locked_until = entry
    if time.time() < locked_until:
        return int(locked_until - time.time())
    if count >= _MAX_ATTEMPTS:
        _failures.pop(ip, None)
    return None


def _record_failure() -> None:
    ip = _client_ip()
    count, _ = _failures.get(ip, (0, 0))
    count += 1
    locked_until = time.time() + _LOCKOUT_SECONDS if count >= _MAX_ATTEMPTS else 0
    _failures[ip] = (count, locked_until)


def _clear_failures() -> None:
    _failures.pop(_client_ip(), None)


def verify_pin(pin: str) -> bool:
    from config import config
    expected = (config.dashboard_pin or "").strip()
    if not _PIN_RE.match(expected) or not _PIN_RE.match(pin.strip()):
        return False
    return hmac.compare_digest(pin.strip(), expected)


def register_auth_routes(bp) -> None:
    @bp.route("/auth/status")
    def auth_status():
        locked = _rate_limited()
        return jsonify({
            "pin_required": pin_required(),
            "authenticated": is_authenticated(),
            "locked_seconds": locked,
        })

    @bp.route("/auth/pin", methods=["POST"])
    def auth_pin():
        from flask import request

        locked = _rate_limited()
        if locked:
            return jsonify({"error": f"Too many attempts. Try again in {locked}s."}), 429
        if not pin_required():
            session.permanent = True
            session["fos_auth"] = True
            return jsonify({"ok": True, "authenticated": True})
        data = request.get_json(silent=True) or {}
        pin = str(data.get("pin") or "").strip()
        if not _PIN_RE.match(pin):
            return jsonify({"error": "Enter a 6-digit PIN"}), 400
        if verify_pin(pin):
            _clear_failures()
            session.permanent = True
            session["fos_auth"] = True
            return jsonify({"ok": True, "authenticated": True})
        _record_failure()
        return jsonify({"error": "Incorrect PIN"}), 401

    @bp.route("/auth/logout", methods=["POST"])
    def auth_logout():
        session.clear()
        return jsonify({"ok": True, "authenticated": False})
