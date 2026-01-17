import httpx
from typing import Any, Optional
import asyncio
from datetime import datetime

from app.config import get_settings


class RateLimiter:
    """Token bucket rate limiter for 40 req/sec (under 50 limit)."""

    def __init__(self, rate: float = 40.0):
        self.rate = rate
        self.tokens = rate
        self.last_update = datetime.now()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = datetime.now()
            elapsed = (now - self.last_update).total_seconds()
            self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


class ProductBoardClient:
    """Async client for ProductBoard API v2."""

    BASE_URL = "https://api.productboard.com"

    def __init__(self, api_token: Optional[str] = None):
        settings = get_settings()
        self.api_token = api_token or settings.productboard_api_token
        self.rate_limiter = RateLimiter()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "X-Version": "1",
        }

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=self.headers,
            timeout=30.0,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
        retries: int = 3,
    ) -> dict[str, Any]:
        """Make a rate-limited request with retries."""
        await self.rate_limiter.acquire()

        for attempt in range(retries):
            try:
                response = await self._client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json,
                )

                if response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = int(response.headers.get("Retry-After", 1))
                    await asyncio.sleep(wait_time)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        return {}

    async def get(self, path: str, params: Optional[dict] = None) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def get_paginated(
        self,
        path: str,
        params: Optional[dict] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch all pages of a paginated endpoint."""
        params = params or {}
        params["pageLimit"] = limit

        all_data = []

        while True:
            response = await self.get(path, params)
            data = response.get("data", [])
            all_data.extend(data)

            # Check for next page
            next_cursor = response.get("pageCursor")

            if not next_cursor or not data:
                break

            params["pageCursor"] = next_cursor

        return all_data
