from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Mount

from notes_mcp.auth import BearerAuthMiddleware
from notes_mcp.tools.notes import register_note_tools
from notes_mcp.tools.reports import register_report_tools
from notes_mcp.tools.sync import register_sync_tools


def create_mcp_app(api_key: str):
    """Create the MCP ASGI app with bearer auth. api_key must be non-empty."""
    server = FastMCP("Notes HQ")

    register_note_tools(server)
    register_report_tools(server)
    register_sync_tools(server)

    raw_app = server.streamable_http_app()

    # FastMCP registers its route at /mcp internally, but FastAPI strips the
    # /mcp mount prefix before forwarding. This wrapper re-adds it so the
    # route matches: "/" → "/mcp", "/foo" → "/mcp/foo".
    async def path_fixed_app(scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            scope = dict(scope)
            path = scope.get("path", "/")
            scope["path"] = "/mcp" + ("" if path == "/" else path)
        await raw_app(scope, receive, send)

    return Starlette(
        routes=[Mount("/", app=path_fixed_app)],
        middleware=[Middleware(BearerAuthMiddleware, api_key=api_key)],
    )
