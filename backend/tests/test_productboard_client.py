# backend/tests/test_productboard_client.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.integrations.productboard.client import ProductBoardClient, RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_acquire():
    limiter = RateLimiter(rate=10.0)
    # Should not block for first few requests
    for _ in range(5):
        await limiter.acquire()
    assert limiter.tokens < 10


@pytest.mark.asyncio
async def test_client_headers():
    client = ProductBoardClient(api_token="test_token")
    assert client.headers["Authorization"] == "Bearer test_token"
    assert "X-Version" in client.headers


@pytest.mark.asyncio
async def test_client_context_manager():
    async with ProductBoardClient(api_token="test") as client:
        assert client._client is not None
