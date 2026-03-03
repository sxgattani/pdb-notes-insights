from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Mount

from mcp.auth import BearerAuthMiddleware
from mcp.tools.notes import register_note_tools
from mcp.tools.reports import register_report_tools
from mcp.tools.sync import register_sync_tools


def create_mcp_app(api_key: str):
    """Create the MCP ASGI app with bearer auth. api_key must be non-empty."""
    server = FastMCP("Notes HQ")

    register_note_tools(server)
    register_report_tools(server)
    register_sync_tools(server)

    raw_app = server.streamable_http_app()

    return Starlette(
        routes=[Mount("/mcp", app=raw_app)],
        middleware=[Middleware(BearerAuthMiddleware, api_key=api_key)],
    )
