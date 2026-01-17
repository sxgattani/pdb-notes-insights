from typing import Optional
from datetime import datetime

from app.integrations.productboard.client import ProductBoardClient


class NotesAPI:
    """ProductBoard Notes API methods."""

    def __init__(self, client: ProductBoardClient):
        self.client = client

    async def list_notes(
        self,
        updated_after: Optional[datetime] = None,
        state: Optional[str] = None,
    ) -> list[dict]:
        """Fetch all notes, optionally filtered."""
        params = {}

        if updated_after:
            params["updatedAfter"] = updated_after.isoformat()
        if state:
            params["state"] = state

        return await self.client.get_paginated("/notes", params)

    async def get_note(self, note_id: str) -> dict:
        """Fetch a single note by ID."""
        response = await self.client.get(f"/notes/{note_id}")
        return response.get("data", {})

    async def get_note_features(self, note_id: str) -> list[dict]:
        """Get features linked to a note."""
        return await self.client.get_paginated(f"/notes/{note_id}/features")
