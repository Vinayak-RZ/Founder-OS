import math

from agent import finance, store


def test_runway_infinite_when_profitable():
    assert finance.runway_months({"cash": 1000, "monthly_burn": 100, "mrr": 200}) == math.inf


def test_runway_normal_case():
    assert finance.runway_months({"cash": 10000, "monthly_burn": 2000, "mrr": 0}) == 5.0


def test_runway_none_when_no_data():
    assert finance.runway_months(None) is None


def test_status_thresholds():
    assert finance._status_for(2) == "critical"
    assert finance._status_for(5) == "warning"
    assert finance._status_for(12) == "healthy"
    assert finance._status_for(math.inf) == "healthy"
    assert finance._status_for(None) == "unknown"


def test_summary_roundtrip_via_store():
    store.set_financials(50000, 10000, 0, "unit-test")
    s = finance.summary()
    assert s["set"] is True
    assert s["runway_months"] == 5.0
    assert s["status"] == "warning"
