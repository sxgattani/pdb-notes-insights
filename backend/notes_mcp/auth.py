import json
from starlette.types import ASGIApp, Scope, Receive, Send


class BearerAuthMiddleware:
    """Pure ASGI bearer auth middleware. Supports streaming/SSE responses."""

    def __init__(self, app: ASGIApp, api_key: str) -> None:
        if not api_key:
            raise ValueError("BearerAuthMiddleware requires a non-empty api_key")
        self.app = app
        self.api_key = api_key

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            auth_bytes = headers.get(b"authorization", b"")
            auth = auth_bytes.decode("latin-1") if isinstance(auth_bytes, bytes) else auth_bytes
            if not auth.startswith("Bearer ") or auth[7:] != self.api_key:
                body = json.dumps({"error": "Unauthorized"}).encode()
                await send({
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                })
                await send({"type": "http.response.body", "body": body, "more_body": False})
                return
        await self.app(scope, receive, send)
