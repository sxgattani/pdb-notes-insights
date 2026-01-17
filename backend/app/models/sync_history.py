from sqlalchemy import Column, Integer, String, DateTime, Text
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
    error_message = Column(Text)
