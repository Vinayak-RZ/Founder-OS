"""Tests for persistent agent history (sessions, runs, artifacts)."""
from __future__ import annotations

import os
import tempfile

import pytest

from memory import agent_history


@pytest.fixture
def history_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setenv("FOUNDER_OS_DB", path)
    import memory.sql_store as sql_store

    monkeypatch.setattr(sql_store, "DB_PATH", path)
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


def test_session_messages_and_run(history_db):
    sid = agent_history.create_session(world_id="w1", specialist="supervisor", title="Review docs")
    agent_history.begin_turn(session_id=sid, world_id="w1", specialist="supervisor")
    agent_history.add_message(sid, "user", "Find ICPs for Stamped")
    trace = {
        "id": "trace001",
        "actor": "user",
        "message": "Find ICPs for Stamped",
        "final": "Here are three ICPs…",
        "duration_s": 12.5,
        "events": [{"type": "tool", "t": 1.2, "data": {"name": "create_document", "decision": "allow"}}],
    }
    run_id = agent_history.persist_run_from_trace(trace)
    agent_history.add_message(sid, "assistant", trace["final"], run_id=run_id)
    agent_history.end_turn()

    detail = agent_history.get_session_detail(sid)
    assert detail is not None
    assert len(detail["messages"]) == 2
    assert len(detail["runs"]) == 1
    assert detail["runs"][0]["tools"][0]["name"] == "create_document"


def test_register_artifact_and_download_path(history_db, monkeypatch, tmp_path):
    docs = tmp_path / "documents"
    docs.mkdir()
    doc_path = docs / "icp_report.md"
    doc_path.write_text("# ICP Report\n", encoding="utf-8")
    monkeypatch.setattr(agent_history, "DOCS_DIR", str(docs))

    agent_history.begin_turn(session_id=agent_history.create_session(title="Doc run"))
    trace = {"id": "run42", "actor": "user", "message": "make doc", "final": "done", "duration_s": 1, "events": []}
    agent_history.persist_run_from_trace(trace)
    art = agent_history.register_artifact(
        kind="md",
        title="ICP Report",
        path=str(doc_path),
        mime_type="text/markdown",
    )
    agent_history.end_turn()

    assert art["id"]
    listed = agent_history.list_artifacts(limit=10)
    assert len(listed) == 1
    assert listed[0]["download_url"] == f"/api/artifacts/{art['id']}/file"
    assert agent_history.artifact_file_path(art["id"]) == str(doc_path.resolve())


def test_history_api(client, no_pin_config, history_db, monkeypatch):
    sid = agent_history.create_session(title="API session")
    agent_history.add_message(sid, "user", "hello")
    agent_history.add_message(sid, "assistant", "hi there")

    r = client.get("/api/history")
    assert r.status_code == 200
    body = r.get_json()
    assert any(s["id"] == sid for s in body["sessions"])

    r2 = client.get(f"/api/history/sessions/{sid}")
    assert r2.status_code == 200
    assert len(r2.get_json()["messages"]) == 2

    arts = client.get("/api/artifacts")
    assert arts.status_code == 200
    assert "artifacts" in arts.get_json()
