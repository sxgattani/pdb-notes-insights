from typing import Optional
from datetime import datetime

from app.integrations.productboard.client import ProductBoardClient


class FeaturesAPI:
    """ProductBoard Features API methods."""

    def __init__(self, client: ProductBoardClient):
        self.client = client

    async def list_features(
        self,
        updated_after: Optional[datetime] = None,
    ) -> list[dict]:
        """Fetch all features."""
        params = {}

        if updated_after:
            params["updatedAfter"] = updated_after.isoformat()

        return await self.client.get_paginated("/features", params)

    async def get_feature(self, feature_id: str) -> dict:
        """Fetch a single feature by ID."""
        response = await self.client.get(f"/features/{feature_id}")
        return response.get("data", {})

    async def get_feature_notes(self, feature_id: str) -> list[dict]:
        """Get notes linked to a feature."""
        return await self.client.get_paginated(f"/features/{feature_id}/notes")
