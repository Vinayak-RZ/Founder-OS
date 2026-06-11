"""In-app notification feed for the web UI.

Scheduler jobs, heartbeats, reminders, and approvals surface here when
Telegram is disabled or as a parallel channel when both are enabled.
"""
import time
import uuid
from threading import Lock

_lock = Lock()
_items: list[dict] = []
_MAX = 200


def push(title: str, body: str, kind: str = "info", meta: dict = None) -> dict:
    item = {
        "id": uuid.uuid4().hex[:12],
        "title": title,
        "body": body,
        "kind": kind,
        "meta": meta or {},
        "ts": time.time(),
        "read": False,
    }
    with _lock:
        _items.insert(0, item)
        del _items[_MAX:]
    return item


def list_items(limit: int = 30, unread_only: bool = False) -> list:
    with _lock:
        items = list(_items)
    if unread_only:
        items = [i for i in items if not i["read"]]
    return items[:limit]


def mark_read(item_id: str) -> bool:
    with _lock:
        for i in _items:
            if i["id"] == item_id:
                i["read"] = True
                return True
    return False


def mark_all_read():
    with _lock:
        for i in _items:
            i["read"] = True


def unread_count() -> int:
    with _lock:
        return sum(1 for i in _items if not i["read"])
