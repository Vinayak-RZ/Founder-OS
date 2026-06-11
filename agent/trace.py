"""Per-turn tracing (observability) with replay support.

Records a structured trace of every turn — the plan, each tool call (args,
decision, result preview, timing), LLM usage, and the final answer — to
data/traces/YYYY-MM-DD.jsonl. This is the agent's flight recorder: it powers
debugging, the replay script, and cost/behavior analysis.

A contextvar holds the "current" trace so the shared executor loop can append
tool events without threading an object through every call.
"""
import contextvars
import json
import os
import time
import uuid

TRACE_DIR = "./data/traces"
_current = contextvars.ContextVar("trace", default=None)


class Trace:
    def __init__(self, actor: str, message: str):
        self.id = uuid.uuid4().hex[:12]
        self.actor = actor
        self.message = message
        self.t0 = time.time()
        self.events = []

    def add(self, etype: str, data: dict):
        self.events.append({"t": round(time.time() - self.t0, 3), "type": etype, "data": data})

    def finish(self, final_text: str):
        record = {
            "id": self.id, "actor": self.actor, "message": self.message[:2000],
            "final": (final_text or "")[:2000], "duration_s": round(time.time() - self.t0, 2),
            "ts": self.t0, "events": self.events,
        }
        try:
            os.makedirs(TRACE_DIR, exist_ok=True)
            path = os.path.join(TRACE_DIR, time.strftime("%Y-%m-%d") + ".jsonl")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except Exception:
            pass
        return record


def start(actor: str, message: str) -> Trace:
    t = Trace(actor, message)
    _current.set(t)
    return t


def current():
    return _current.get()


def add(etype: str, data: dict):
    t = _current.get()
    if t is not None:
        t.add(etype, data)


def add_tool_event(name: str, args: dict, decision: str, result):
    t = _current.get()
    if t is None:
        return
    preview = result if isinstance(result, str) else json.dumps(result, default=str)
    t.add("tool", {"name": name, "decision": decision,
                   "args": {k: str(v)[:120] for k, v in (args or {}).items()},
                   "result_preview": (preview or "")[:300]})
    try:
        from dashboard.live_ops import add_tool
        add_tool(name, decision)
    except Exception:
        pass


def finish(final_text: str):
    t = _current.get()
    if t is not None:
        rec = t.finish(final_text)
        _current.set(None)
        return rec
    return None


def _read_recent_lines(n: int) -> list:
    path = os.path.join(TRACE_DIR, time.strftime("%Y-%m-%d") + ".jsonl")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.readlines()[-n:]
    except Exception:
        return []


def recent(n: int = 5) -> list:
    """Return the last n traces from today's file (newest first)."""
    try:
        out = []
        for ln in reversed(_read_recent_lines(n)):
            r = json.loads(ln)
            out.append({"id": r["id"], "actor": r["actor"], "message": r["message"][:100],
                        "tools": [e["data"]["name"] for e in r["events"] if e["type"] == "tool"],
                        "duration_s": r["duration_s"]})
        return out
    except Exception:
        return []


def recent_full(n: int = 12) -> list:
    """Full trace records including tool events (for activity visualization)."""
    try:
        out = []
        for ln in reversed(_read_recent_lines(n)):
            r = json.loads(ln)
            events = []
            for e in r.get("events", []):
                if e.get("type") == "tool":
                    d = e.get("data", {})
                    events.append({
                        "t": e.get("t", 0),
                        "name": d.get("name", ""),
                        "decision": d.get("decision", ""),
                        "preview": (d.get("result_preview") or "")[:120],
                    })
            out.append({
                "id": r["id"],
                "actor": r["actor"],
                "message": r["message"][:200],
                "final": (r.get("final") or "")[:200],
                "duration_s": r.get("duration_s", 0),
                "ts": r.get("ts"),
                "events": events,
            })
        return out
    except Exception:
        return []
