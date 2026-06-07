"""MCP server — expose Founder OS tools to any Model Context Protocol client.

Run this and point an MCP client (Claude Desktop, Cursor, etc.) at it to drive the
same tools the agent uses: memory, CRM, research, outreach drafting, finance,
GraphRAG, documents, and more. The agent's full capability surface, standardized.

Safety is preserved: approval-gated actions (send_email, x_post, create_tool, …) are
NOT executed directly for an external client — they're queued to the founder's
Telegram approval gate, exactly like the agent's own loop. So an MCP client can
*propose* sending an email, but only the founder's tap actually sends it (unless
AUTO_APPROVE / AUTONOMY_LEVEL=autonomous is set).

Usage:
    pip install mcp
    python mcp_server.py            # speaks MCP over stdio

Example Claude Desktop / Cursor config:
    {
      "mcpServers": {
        "founder-os": { "command": "python", "args": ["mcp_server.py"] }
      }
    }
"""
import asyncio
import json
import logging

from agent import registry, approvals
import agent.tools  # noqa: F401 — registers the full tool catalog
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")


def tool_specs() -> list:
    """(name, description, json_schema) for every registered tool."""
    return [(t.name, t.description, t.parameters) for t in registry.all_tools()]


async def run_tool(name: str, arguments: dict):
    """Execute a tool for an MCP client, honoring the approval gate."""
    tool = registry.get(name)
    if tool is None:
        return {"error": f"Unknown tool: {name}"}
    arguments = arguments or {}
    # Keep the human-in-the-loop: gated actions go to the Telegram approval queue.
    if tool.requires_approval and not (config.auto_approve or config.autonomy_level == "autonomous"):
        return approvals.enqueue(name, arguments)
    return await registry.call(name, arguments)


def build_server():
    from mcp.server import Server
    import mcp.types as types

    server = Server("founder-os")

    @server.list_tools()
    async def _list_tools():
        return [types.Tool(name=n, description=d, inputSchema=p) for n, d, p in tool_specs()]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict):
        result = await run_tool(name, arguments)
        return [types.TextContent(type="text", text=json.dumps(result, default=str)[:8000])]

    return server


async def main_stdio():
    from mcp.server.stdio import stdio_server
    server = build_server()
    logger.info(f"Founder OS MCP server: exposing {len(registry.all_tools())} tools over stdio.")
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    try:
        import mcp  # noqa: F401
    except Exception:
        print("MCP SDK not installed. Install it with:  pip install mcp")
        raise SystemExit(1)
    asyncio.run(main_stdio())
