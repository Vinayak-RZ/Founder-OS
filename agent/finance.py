"""Runway / financial-health math.

Centralizes the runway calculation so both the finance tools and the Founder
World Model report the same numbers. Runway is based on *net* burn (gross monthly
burn minus MRR): if MRR covers burn, the company is cash-flow positive and runway
is effectively unlimited.
"""
import math

from agent import store

CRITICAL_MONTHS = 3
WARNING_MONTHS = 6


def runway_months(fin: dict):
    """Months of cash left. Returns math.inf if cash-flow positive, None if unknown."""
    if not fin:
        return None
    cash = fin.get("cash") or 0
    net_burn = (fin.get("monthly_burn") or 0) - (fin.get("mrr") or 0)
    if net_burn <= 0:
        return math.inf
    return round(cash / net_burn, 1)


def _status_for(months) -> str:
    if months is None:
        return "unknown"
    if months == math.inf:
        return "healthy"
    if months < CRITICAL_MONTHS:
        return "critical"
    if months < WARNING_MONTHS:
        return "warning"
    return "healthy"


def summary() -> dict:
    """Structured financial snapshot with computed runway + health status."""
    fin = store.latest_financials()
    if not fin:
        return {
            "set": False,
            "message": "No financials recorded yet. Use set_financials with cash, "
                       "monthly_burn and (optional) mrr to enable runway tracking.",
        }
    months = runway_months(fin)
    out = {
        "set": True,
        "cash": fin.get("cash"),
        "monthly_burn": fin.get("monthly_burn"),
        "mrr": fin.get("mrr") or 0,
        "net_burn": round((fin.get("monthly_burn") or 0) - (fin.get("mrr") or 0), 2),
        "status": _status_for(months),
        "as_of": fin.get("created_at"),
    }
    if months == math.inf:
        out["runway"] = "cash-flow positive (MRR >= burn)"
    elif months is not None:
        out["runway_months"] = months
    if fin.get("note"):
        out["note"] = fin["note"]
    return out


def warning_line() -> str:
    """Short proactive warning for the world model, or '' if nothing to flag."""
    s = summary()
    if not s.get("set"):
        return ""
    months = s.get("runway_months")
    if s["status"] == "critical":
        return f"🚨 Runway critical: ~{months} months of cash left (cash ${s['cash']:,.0f}, net burn ${s['net_burn']:,.0f}/mo)."
    if s["status"] == "warning":
        return f"⚠ Runway tightening: ~{months} months left (cash ${s['cash']:,.0f}, net burn ${s['net_burn']:,.0f}/mo)."
    return ""
