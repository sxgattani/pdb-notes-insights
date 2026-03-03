import pytest
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.middleware import Middleware

from notes_mcp.auth import BearerAuthMiddleware


def homepage(request):
    return PlainTextResponse("ok")


def make_app(api_key: str):
    return Starlette(
        routes=[Route("/", homepage)],
        middleware=[Middleware(BearerAuthMiddleware, api_key=api_key)],
    )


def test_missing_auth_header_returns_401():
    app = make_app("secret")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/")
    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized"}


def test_wrong_token_returns_401():
    app = make_app("secret")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/", headers={"Authorization": "Bearer wrongtoken"})
    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized"}


def test_correct_token_passes_through():
    app = make_app("secret")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/", headers={"Authorization": "Bearer secret"})
    assert response.status_code == 200
    assert response.text == "ok"


def test_non_bearer_scheme_returns_401():
    app = make_app("secret")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/", headers={"Authorization": "Basic secret"})
    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized"}


def test_empty_api_key_raises_on_startup():
    # Starlette builds the middleware stack lazily; trigger it explicitly so
    # the ValueError raised in BearerAuthMiddleware.__init__ is surfaced.
    with pytest.raises(ValueError, match="non-empty api_key"):
        app = Starlette(
            routes=[Route("/", homepage)],
            middleware=[Middleware(BearerAuthMiddleware, api_key="")],
        )
        app.build_middleware_stack()
