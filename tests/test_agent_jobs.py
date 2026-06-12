"""Tests for background agent jobs."""
from __future__ import annotations

import os
import tempfile
import time

import pytest


@pytest.fixture
def history_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setenv("FOUNDER_OS_DB", path)
    import memory.sql_store as sql_store

    monkeypatch.setattr(sql_store, "DB_PATH", path)
    from memory import agent_history

    agent_history.init_agent_history_db()
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture
def client():
    from dashboard.app import app

    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def no_pin_config(monkeypatch):
    from config import config as app_config

    monkeypatch.setattr(app_config, "dashboard_pin", "")
    return ""


def test_start_and_get_job(monkeypatch, history_db):
    from dashboard import agent_jobs

    def _instant(job_id):
        with agent_jobs._lock:
            j = agent_jobs._jobs.get(job_id)
            if j:
                agent_jobs._set_status(j, "completed", result="ok", phase="Complete")

    monkeypatch.setattr(agent_jobs, "_run_job_thread", _instant)
    job = agent_jobs.start_job(mode="chat", message="hello test")
    assert job["id"]
    time.sleep(0.05)
    final = agent_jobs.get_job(job["id"])
    assert final["status"] == "completed"


def test_chat_async_api(client, no_pin_config, history_db, monkeypatch):
    from config import config as app_config

    monkeypatch.setattr(app_config, "agent_paused", True)
    r = client.post("/api/chat/async", json={"message": "ping"})
    assert r.status_code == 200
    job_id = r.get_json()["job"]["id"]
    r2 = client.get(f"/api/chat/jobs/{job_id}")
    assert r2.status_code == 200
    assert r2.get_json()["job"]["id"] == job_id
