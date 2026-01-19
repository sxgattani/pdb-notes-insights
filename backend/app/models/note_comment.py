from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class NoteComment(Base):
    """Comment on a note - storing most recent 5 per note."""
    __tablename__ = "note_comments"

    id = Column(Integer, primary_key=True, index=True)
    pb_id = Column(String, unique=True, nullable=False, index=True)
    content = Column(Text)
    timestamp = Column(DateTime(timezone=True), index=True)
    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    # Foreign keys
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True)

    # Relationships
    note = relationship("Note", back_populates="comments")
    member = relationship("Member")
