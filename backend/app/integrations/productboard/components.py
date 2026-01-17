from app.integrations.productboard.client import ProductBoardClient


class ComponentsAPI:
    """ProductBoard Components API methods."""

    def __init__(self, client: ProductBoardClient):
        self.client = client

    async def list_components(self) -> list[dict]:
        """Fetch all components (product hierarchy)."""
        return await self.client.get_paginated("/components")

    async def get_component(self, component_id: str) -> dict:
        """Fetch a single component by ID."""
        response = await self.client.get(f"/components/{component_id}")
        return response.get("data", {})
