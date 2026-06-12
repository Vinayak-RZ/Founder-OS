from config import config as app_config

from dashboard.auth import path_exempt, pin_required, verify_pin


def test_path_exempt():
    assert path_exempt("/")
    assert path_exempt("/static/app.js")
    assert path_exempt("/api/auth/pin")
    assert not path_exempt("/api/state")


def test_verify_pin(monkeypatch):
    monkeypatch.setattr(app_config, "dashboard_pin", "482910")
    assert verify_pin("482910")
    assert not verify_pin("000000")


def test_pin_required_empty(monkeypatch):
    monkeypatch.setattr(app_config, "dashboard_pin", "")
    assert not pin_required()
