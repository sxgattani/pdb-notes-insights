from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.types import ASGIApp, Scope, Receive, Send

from notes_mcp.auth import BearerAuthMiddleware
from notes_mcp.tools.notes import register_note_tools
from notes_mcp.tools.reports import register_report_tools
from notes_mcp.tools.sync import register_sync_tools


def create_mcp_components(api_key: str):
    """Create MCP server components.

    Returns (raw_app, MCPMiddleware):
        raw_app      — FastMCP's Starlette app with a lifespan that must be started
                       before handling requests (it initializes the session task group).
        MCPMiddleware — ASGI middleware class; routes /mcp paths to raw_app wrapped
                        in bearer auth, bypassing FastAPI's route matching entirely.
    """
    # Disable FastMCP's DNS rebinding protection — we authenticate via bearer
    # token in BearerAuthMiddleware, making host-header DNS rebinding irrelevant.
    server = FastMCP(
        "Notes HQ",
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        ),
    )

    register_note_tools(server)
    register_report_tools(server)
    register_sync_tools(server)

    # raw_app serves at /mcp and owns the MCP session lifecycle (must run lifespan).
    raw_app = server.streamable_http_app()
    auth_app = BearerAuthMiddleware(app=raw_app, api_key=api_key)

    class MCPMiddleware:
        """Routes /mcp and /mcp/* to the MCP app before FastAPI routing.

        Starlette's Mount("/mcp") returns NONE (not even PARTIAL) for the exact
        path /mcp (no trailing slash), so requests fall through to the catch-all
        GET route and get 405. This middleware intercepts at the ASGI level instead.
        """

        def __init__(self, app: ASGIApp) -> None:
            self.app = app

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            path = scope.get("path", "")
            if path == "/mcp" or path.startswith("/mcp/"):
                await auth_app(scope, receive, send)
            else:
                await self.app(scope, receive, send)

    return raw_app, MCPMiddleware
