from typing import Optional
from datetime import datetime

from app.integrations.productboard.client import ProductBoardClient


class CustomersAPI:
    """ProductBoard Customers API methods (called 'users' in PB API)."""

    def __init__(self, client: ProductBoardClient):
        self.client = client

    async def list_customers(
        self,
        updated_after: Optional[datetime] = None,
    ) -> list[dict]:
        """Fetch all customers (external users in ProductBoard)."""
        params = {}

        if updated_after:
            params["updatedAfter"] = updated_after.isoformat()

        # Note: ProductBoard calls these "customers" in some contexts
        return await self.client.get_paginated("/customers", params)

    async def get_customer(self, customer_id: str) -> dict:
        """Fetch a single customer by ID."""
        response = await self.client.get(f"/customers/{customer_id}")
        return response.get("data", {})
