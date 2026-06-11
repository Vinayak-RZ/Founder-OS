"""In-memory live operation feed for the web UI (thread-safe)."""
import threading
import time
from typing import Any

_lock = threading.Lock()
_state: dict[str, Any] = {
    "active": False,
    "actor": "",
    "message": "",
    "phase": "",
    "started_at": None,
    "events": [],
}


def begin(actor: str, message: str) -> None:
    with _lock:
        _state.update({
            "active": True,
            "actor": actor,
            "message": (message or "")[:500],
            "phase": "Starting…",
            "started_at": time.time(),
            "events": [],
        })


def set_phase(phase: str) -> None:
    with _lock:
        if not _state["active"]:
            return
        _state["phase"] = phase
        _state["events"].append({
            "t": round(time.time() - (_state["started_at"] or time.time()), 2),
            "type": "phase",
            "label": phase,
        })
        _state["events"] = _state["events"][-40:]


def add_tool(name: str, decision: str) -> None:
    with _lock:
        if not _state["active"]:
            return
        _state["phase"] = f"Running {name}"
        _state["events"].append({
            "t": round(time.time() - (_state["started_at"] or time.time()), 2),
            "type": "tool",
            "name": name,
            "decision": decision,
        })
        _state["events"] = _state["events"][-40:]


def end() -> None:
    with _lock:
        _state["active"] = False
        _state["phase"] = "Idle"


def snapshot() -> dict:
    with _lock:
        out = dict(_state)
        out["events"] = list(_state["events"])
        if out["started_at"]:
            out["elapsed_s"] = round(time.time() - out["started_at"], 1) if out["active"] else 0
        return out
