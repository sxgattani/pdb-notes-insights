from typing import Optional
from datetime import datetime

from app.integrations.productboard.client import ProductBoardClient


class CompaniesAPI:
    """ProductBoard Companies API methods."""

    def __init__(self, client: ProductBoardClient):
        self.client = client

    async def list_companies(
        self,
        updated_after: Optional[datetime] = None,
    ) -> list[dict]:
        """Fetch all companies."""
        params = {}

        if updated_after:
            params["updatedAfter"] = updated_after.isoformat()

        return await self.client.get_paginated("/companies", params)

    async def get_company(self, company_id: str) -> dict:
        """Fetch a single company by ID."""
        response = await self.client.get(f"/companies/{company_id}")
        return response.get("data", {})
