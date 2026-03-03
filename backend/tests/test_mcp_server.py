"""
Smoke tests for MCP server wiring.
NOTE: These tests require Python 3.10+ (mcp library constraint).
They are skipped automatically on Python 3.9.
"""
import sys
import pytest

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="mcp library requires Python 3.10+"
)


def test_mcp_app_returns_401_without_token():
    from mcp.server import create_mcp_app
    from starlette.testclient import TestClient
    app = create_mcp_app(api_key="testsecret")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/")
    assert response.status_code == 401


def test_mcp_app_accessible_with_token():
    from mcp.server import create_mcp_app
    from starlette.testclient import TestClient
    app = create_mcp_app(api_key="testsecret")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/mcp", headers={"Authorization": "Bearer testsecret"}, json={})
    assert response.status_code != 401
