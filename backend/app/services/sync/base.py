from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional, TypeVar, Generic
from sqlalchemy.orm import Session

from app.models import SyncHistory

T = TypeVar("T")

# Full sync interval in days
FULL_SYNC_INTERVAL_DAYS = 7


class BaseSyncer(ABC, Generic[T]):
    """Base class for entity syncers."""

    entity_type: str = ""

    def __init__(self, db: Session):
        self.db = db
        self.sync_history: Optional[SyncHistory] = None
        self._is_full_sync: bool = False

    def start_sync(self, is_full_sync: bool = False) -> SyncHistory:
        """Record sync start."""
        self._is_full_sync = is_full_sync
        self.sync_history = SyncHistory(
            entity_type=self.entity_type,
            status="running",
            is_full_sync=is_full_sync,
        )
        self.db.add(self.sync_history)
        self.db.commit()
        return self.sync_history

    def complete_sync(self, records_synced: int, records_deleted: int = 0):
        """Record sync completion."""
        if self.sync_history:
            self.sync_history.status = "completed"
            self.sync_history.completed_at = datetime.now(timezone.utc)
            self.sync_history.records_synced = records_synced
            self.sync_history.records_deleted = records_deleted
            self.db.commit()

    def fail_sync(self, error_message: str):
        """Record sync failure."""
        if self.sync_history:
            self.sync_history.status = "failed"
            self.sync_history.completed_at = datetime.now(timezone.utc)
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

    def get_last_full_sync_time(self) -> Optional[datetime]:
        """Get the last successful full sync time for this entity type."""
        last_full_sync = (
            self.db.query(SyncHistory)
            .filter(
                SyncHistory.entity_type == self.entity_type,
                SyncHistory.status == "completed",
                SyncHistory.is_full_sync == True,
            )
            .order_by(SyncHistory.completed_at.desc())
            .first()
        )
        return last_full_sync.completed_at if last_full_sync else None

    def needs_full_sync(self) -> bool:
        """Check if a full sync is needed (never done or 7+ days since last)."""
        last_full_sync = self.get_last_full_sync_time()
        if not last_full_sync:
            return True

        # Ensure timezone-aware comparison
        if last_full_sync.tzinfo is None:
            last_full_sync = last_full_sync.replace(tzinfo=timezone.utc)

        time_since_full_sync = datetime.now(timezone.utc) - last_full_sync
        return time_since_full_sync >= timedelta(days=FULL_SYNC_INTERVAL_DAYS)

    @abstractmethod
    async def sync(self) -> int:
        """Perform the sync. Returns number of records synced."""
        pass
