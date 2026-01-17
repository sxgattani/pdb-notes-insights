from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, TypeVar, Generic
from sqlalchemy.orm import Session

from app.models import SyncHistory

T = TypeVar("T")


class BaseSyncer(ABC, Generic[T]):
    """Base class for entity syncers."""

    entity_type: str = ""

    def __init__(self, db: Session):
        self.db = db
        self.sync_history: Optional[SyncHistory] = None

    def start_sync(self) -> SyncHistory:
        """Record sync start."""
        self.sync_history = SyncHistory(
            entity_type=self.entity_type,
            status="running",
        )
        self.db.add(self.sync_history)
        self.db.commit()
        return self.sync_history

    def complete_sync(self, records_synced: int):
        """Record sync completion."""
        if self.sync_history:
            self.sync_history.status = "completed"
            self.sync_history.completed_at = datetime.utcnow()
            self.sync_history.records_synced = records_synced
            self.db.commit()

    def fail_sync(self, error_message: str):
        """Record sync failure."""
        if self.sync_history:
            self.sync_history.status = "failed"
            self.sync_history.completed_at = datetime.utcnow()
            self.sync_history.error_message = error_message
            self.db.commit()

    def get_last_sync_time(self) -> Optional[datetime]:
        """Get the last successful sync time for this entity type."""
        last_sync = (
            self.db.query(SyncHistory)
            .filter(
                SyncHistory.entity_type == self.entity_type,
                SyncHistory.status == "completed",
            )
            .order_by(SyncHistory.completed_at.desc())
            .first()
        )
        return last_sync.completed_at if last_sync else None

    @abstractmethod
    async def sync(self) -> int:
        """Perform the sync. Returns number of records synced."""
        pass
