"""Integration tests for dashboard HTTP API (auth gate + core routes)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from dashboard.auth import path_exempt, verify_pin

TEST_PIN = "482910"


@pytest.fixture
def pin_config(monkeypatch):
    cfg = SimpleNamespace(dashboard_pin=TEST_PIN)
    monkeypatch.setattr("config.config", cfg)
    return cfg


@pytest.fixture
def no_pin_config(monkeypatch):
    cfg = SimpleNamespace(dashboard_pin="")
    monkeypatch.setattr("config.config", cfg)
    return cfg


@pytest.fixture
def client():
    from dashboard.app import app  # noqa: PLC0415 — lazy import avoids collection-time side effects

    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _login(client, pin: str = TEST_PIN):
    return client.post("/api/auth/pin", json={"pin": pin})


def test_github_callback_exempt():
    assert path_exempt("/api/github/callback")


def test_health_unauthenticated(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert body["storage"] in ("s3", "local")


def test_auth_status_reports_pin_required(client, pin_config):
    r = client.get("/api/auth/status")
    assert r.status_code == 200
    body = r.get_json()
    assert body["pin_required"] is True
    assert body["authenticated"] is False


def test_state_blocked_without_pin(client, pin_config):
    r = client.get("/api/state")
    assert r.status_code == 401
    assert r.get_json()["pin_required"] is True


def test_pin_wrong_then_correct(client, pin_config):
    bad = _login(client, "000000")
    assert bad.status_code == 401

    ok = _login(client, TEST_PIN)
    assert ok.status_code == 200
    assert ok.get_json()["authenticated"] is True

    r = client.get("/api/state")
    assert r.status_code == 200
    body = r.get_json()
    assert "config" in body
    assert "worlds" in body


def test_logout_clears_session(client, pin_config):
    _login(client, TEST_PIN)
    out = client.post("/api/auth/logout")
    assert out.status_code == 200
    assert out.get_json()["authenticated"] is False

    r = client.get("/api/state")
    assert r.status_code == 401


def test_worlds_templates_tools_when_authenticated(client, pin_config):
    _login(client, TEST_PIN)

    worlds = client.get("/api/worlds")
    assert worlds.status_code == 200
    tree = worlds.get_json()
    assert "root" in tree or "children" in tree or isinstance(tree, dict)

    templates = client.get("/api/world-templates")
    assert templates.status_code == 200
    assert "templates" in templates.get_json()

    tools = client.get("/api/tools")
    assert tools.status_code == 200
    assert tools.get_json()["total"] >= 0


def test_goals_crm_crud_when_authenticated(client, pin_config):
    _login(client, TEST_PIN)

    goal = client.post("/api/goals", json={"title": "API test goal", "priority": 2})
    assert goal.status_code == 200
    gid = goal.get_json()["id"]

    goals = client.get("/api/goals")
    assert goals.status_code == 200

    done = client.patch(f"/api/goals/{gid}", json={"status": "done"})
    assert done.status_code == 200

    contact = client.post(
        "/api/crm/contacts",
        json={"name": "API Test Contact", "company": "Founder OS", "status": "prospect"},
    )
    assert contact.status_code == 200
    cid = contact.get_json()["id"]

    crm = client.get("/api/crm/contacts")
    assert crm.status_code == 200
    assert "contacts" in crm.get_json()

    patched = client.patch(f"/api/crm/contacts/{cid}", json={"status": "contacted"})
    assert patched.status_code == 200


def test_world_create_and_vault_when_authenticated(client, pin_config):
    _login(client, TEST_PIN)

    created = client.post(
        "/api/worlds",
        json={"name": "API Test World", "kind": "startup", "description": "integration test"},
    )
    assert created.status_code == 200
    world = created.get_json()["world"]
    wid = world["id"]

    vault = client.get(f"/api/worlds/{wid}/vault")
    assert vault.status_code == 200
    body = vault.get_json()
    assert body["world"]["id"] == wid
    assert "vault_graph" in body
    assert body["vault_graph"]["nodes"]

    docs = client.get(f"/api/worlds/{wid}/vault/documents")
    assert docs.status_code == 200
    assert "documents" in docs.get_json()

    deleted = client.delete(f"/api/worlds/{wid}")
    assert deleted.status_code == 200


def test_no_pin_allows_state_directly(client, no_pin_config):
    r = client.get("/api/state")
    assert r.status_code == 200


def test_verify_pin_unit(pin_config):
    assert verify_pin(TEST_PIN)
    assert not verify_pin("000000")


def test_infrastructure_health_requires_pin_then_ok(client, pin_config):
    assert client.get("/api/infrastructure/health").status_code == 401
    _login(client, TEST_PIN)
    r = client.get("/api/infrastructure/health?probe=0")
    assert r.status_code == 200
    body = r.get_json()
    assert "host" in body
    assert "s3" in body
    assert "disk" in body
    assert "app" in body


def test_sync_job_endpoints(client, pin_config, monkeypatch):
    import tempfile
    from memory import sync_jobs as sj

    path = tempfile.mktemp(suffix=".db")
    monkeypatch.setenv("FOUNDER_OS_DB", path)
    sj.init_sync_jobs_db()
    job = sj.create_job(
        world_id="w1",
        link_id=1,
        full_name="o/r",
        branch="main",
        world_slug="w1",
        template_id="startup",
        manifest=[],
    )
    _login(client, TEST_PIN)
    r = client.get(f"/api/sync-jobs/{job['id']}")
    assert r.status_code == 200
    assert r.get_json()["id"] == job["id"]

    with patch("integrations.github_sync.process_sync_batch", return_value={"id": job["id"], "done": True, "imported": 0}):
        b = client.post(f"/api/sync-jobs/{job['id']}/batch", json={"batch_size": 4})
    assert b.status_code == 200
    assert b.get_json()["done"] is True
