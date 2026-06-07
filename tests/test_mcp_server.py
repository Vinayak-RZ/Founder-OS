"""MCP server tests — the routing layer, no MCP SDK or network required."""
import asyncio

import mcp_server
from config import config


def test_tool_specs_nonempty_and_well_formed():
    specs = mcp_server.tool_specs()
    assert len(specs) > 20
    for name, desc, schema in specs[:5]:
        assert isinstance(name, str) and name
        assert isinstance(desc, str)
        assert isinstance(schema, dict) and schema.get("type") == "object"


def test_unknown_tool_returns_error():
    out = asyncio.run(mcp_server.run_tool("does_not_exist", {}))
    assert "error" in out


def test_approval_gated_tool_is_queued_not_executed(monkeypatch):
    monkeypatch.setattr(config, "auto_approve", False)
    monkeypatch.setattr(config, "autonomy_level", "balanced")
    out = asyncio.run(mcp_server.run_tool("send_email", {
        "to_address": "a@b.com", "subject": "Hi", "body": "Hello"}))
    # Routed to the approval gate rather than actually sending.
    assert out.get("status") == "pending_approval"
    assert "approval_id" in out


def test_safe_tool_executes(monkeypatch):
    async def fake_call(name, args):
        return {"ok": True, "name": name}
    monkeypatch.setattr(mcp_server.registry, "call", fake_call)
    out = asyncio.run(mcp_server.run_tool("world_state", {}))
    assert out == {"ok": True, "name": "world_state"}
