import asyncio

from agent import approvals, registry


def _register_demo_tool():
    @registry.register(
        name="t_demo_action",
        description="demo",
        parameters={
            "type": "object",
            "properties": {"target": {"type": "string"}, "note": {"type": "string"}},
            "required": ["target"],
        },
    )
    def _demo(target, note=""):
        return {"ok": True, "target": target, "note": note}


def test_missing_required_detects_absent_arg():
    _register_demo_tool()
    assert approvals._missing_required("t_demo_action", {"note": "x"}) == ["target"]
    assert approvals._missing_required("t_demo_action", {"target": "y"}) == []


def test_enqueue_rejects_incomplete_call():
    _register_demo_tool()
    res = approvals.enqueue("t_demo_action", {"note": "x"})
    assert res["status"] == "invalid_approval"
    assert "target" in res["error"]


def test_enqueue_then_approve_executes():
    _register_demo_tool()
    res = approvals.enqueue("t_demo_action", {"target": "acme"})
    assert res["status"] == "pending_approval"
    aid = res["approval_id"]
    out = asyncio.run(approvals.approve(aid))
    assert "Done" in out or "✅" in out


def test_reject_marks_rejected():
    _register_demo_tool()
    res = approvals.enqueue("t_demo_action", {"target": "acme"})
    aid = res["approval_id"]
    out = approvals.reject(aid)
    assert "Rejected" in out or "🚫" in out
