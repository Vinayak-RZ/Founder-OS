"""Finance / runway tracking tools.

Lets the founder record cash, burn and MRR so the agent can compute runway and
proactively warn (via the world model / heartbeat) when cash is running low.
"""
from agent.registry import register
from agent import store, finance


@register(
    name="set_financials",
    description="Record the company's current finances so the agent can track runway and warn "
                "you proactively. Provide cash in the bank, gross monthly burn, and optional MRR. "
                "Call this whenever the numbers change (e.g. after a raise or a new customer).",
    parameters={
        "type": "object",
        "properties": {
            "cash": {"type": "number", "description": "Cash currently in the bank (in your currency)."},
            "monthly_burn": {"type": "number", "description": "Total gross monthly spend."},
            "mrr": {"type": "number", "description": "Monthly recurring revenue (default 0)."},
            "note": {"type": "string", "description": "Optional context (e.g. 'post-seed', 'after hire')."},
        },
        "required": ["cash", "monthly_burn"],
    },
    category="finance",
)
def set_financials(cash, monthly_burn, mrr=0, note=""):
    store.set_financials(float(cash), float(monthly_burn), float(mrr or 0), note or "")
    return finance.summary()


@register(
    name="financial_status",
    description="Get current financial health: cash, burn, MRR, net burn, computed runway in "
                "months, and a status (healthy/warning/critical). Use when asked about money or runway.",
    parameters={"type": "object", "properties": {}},
    category="finance",
)
def financial_status():
    return finance.summary()
