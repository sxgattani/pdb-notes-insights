from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func

from app.database import Base


class SyncHistory(Base):
    __tablename__ = "sync_history"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, index=True)  # notes, features, customers, etc.
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    status = Column(String)  # running, completed, partial, failed
    records_synced = Column(Integer, default=0)
    records_deleted = Column(Integer, default=0)  # soft-deleted records in full sync
    is_full_sync = Column(Boolean, default=False)  # True if this was a full sync
    error_message = Column(Text)
