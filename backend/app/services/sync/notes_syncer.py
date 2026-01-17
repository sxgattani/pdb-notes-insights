from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.services.sync.base import BaseSyncer
from app.models import Note, User, Team, Customer
from app.integrations.productboard import ProductBoardClient, NotesAPI


class NotesSyncer(BaseSyncer[Note]):
    """Syncs notes from ProductBoard."""

    entity_type = "notes"

    async def sync(self) -> int:
        """Sync notes from ProductBoard (incremental)."""
        self.start_sync()
        last_sync = self.get_last_sync_time()

        try:
            async with ProductBoardClient() as client:
                api = NotesAPI(client)
                pb_notes = await api.list_notes(updated_after=last_sync)

            count = 0
            for pb_note in pb_notes:
                self._upsert_note(pb_note)
                count += 1

            self.db.commit()
            self.complete_sync(count)
            return count

        except Exception as e:
            self.fail_sync(str(e))
            raise

    def _upsert_note(self, pb_note: dict):
        """Insert or update a note."""
        pb_id = pb_note.get("id")

        note = self.db.query(Note).filter(Note.pb_id == pb_id).first()

        if not note:
            note = Note(pb_id=pb_id)
            self.db.add(note)

        note.title = pb_note.get("title")
        note.content = pb_note.get("content")
        note.type = pb_note.get("type")
        note.source = pb_note.get("source")
        note.state = pb_note.get("state", "unprocessed")

        # Parse dates
        if pb_note.get("createdAt"):
            note.created_at = datetime.fromisoformat(
                pb_note["createdAt"].replace("Z", "+00:00")
            )
        if pb_note.get("updatedAt"):
            note.updated_at = datetime.fromisoformat(
                pb_note["updatedAt"].replace("Z", "+00:00")
            )

        # Handle state change for processed_at
        if note.state == "processed" and not note.processed_at:
            note.processed_at = datetime.utcnow()

        # Resolve owner
        owner_data = pb_note.get("owner", {})
        if owner_data.get("id"):
            owner = self.db.query(User).filter(
                User.pb_id == owner_data["id"]
            ).first()
            if owner:
                note.owner_id = owner.id

        # Resolve customer
        customer_data = pb_note.get("customer", {})
        if customer_data.get("id"):
            customer = self.db.query(Customer).filter(
                Customer.pb_id == customer_data["id"]
            ).first()
            if customer:
                note.customer_id = customer.id

        # Store extra fields in custom_fields
        known_fields = {
            "id", "title", "content", "type", "source", "state",
            "createdAt", "updatedAt", "owner", "customer", "team"
        }
        custom = {k: v for k, v in pb_note.items() if k not in known_fields}
        if custom:
            note.custom_fields = custom
