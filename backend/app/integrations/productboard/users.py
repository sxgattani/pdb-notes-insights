from app.integrations.productboard.client import ProductBoardClient


class UsersAPI:
    """ProductBoard Users API methods (internal team members)."""

    def __init__(self, client: ProductBoardClient):
        self.client = client

    async def list_users(self) -> list[dict]:
        """Fetch all workspace members."""
        return await self.client.get_paginated("/users")

    async def get_user(self, user_id: str) -> dict:
        """Fetch a single user by ID."""
        response = await self.client.get(f"/users/{user_id}")
        return response.get("data", {})
