from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Feature(Base):
    """Simplified Feature model - stores references from notes."""
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, index=True)
    pb_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)  # fetched separately if needed
    display_url = Column(String)  # link to ProductBoard
    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    notes = relationship("Note", secondary="note_features", back_populates="features")
