from sqlalchemy import Column, Integer, DateTime, ForeignKey, Table
from sqlalchemy.sql import func

from app.database import Base


class NoteFeature(Base):
    __tablename__ = "note_features"

    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    feature_id = Column(Integer, ForeignKey("features.id", ondelete="CASCADE"), primary_key=True)
    linked_at = Column(DateTime(timezone=True), server_default=func.now())
