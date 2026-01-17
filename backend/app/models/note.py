from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    pb_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String)
    content = Column(Text)
    type = Column(String)  # simple, conversation, opportunity
    source = Column(String)
    state = Column(String, index=True)  # processed, unprocessed
    processed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    creator_id = Column(Integer, ForeignKey("users.id"), index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)

    # Extensibility
    custom_fields = Column(JSON().with_variant(JSONB, "postgresql"))

    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    creator = relationship("User", foreign_keys=[creator_id])
    owner = relationship("User", foreign_keys=[owner_id])
    team = relationship("Team")
    customer = relationship("Customer")
