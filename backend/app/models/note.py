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
    state = Column(String, index=True)  # processed, unprocessed
    source_origin = Column(String, index=True)  # feature_request, etc.
    opportunity_type = Column(String, index=True)       # Customer, Prospect, Internal
    product_area = Column(String, index=True)           # D&R, CIEM, etc.
    customer_impact = Column(String, index=True)        # e.g. Moderate pain...
    functionality_timeline = Column(String, index=True) # 3 Months, 6 Months, etc.
    display_url = Column(String)  # link to ProductBoard
    external_display_url = Column(String)  # external link if any
    tags = Column(JSON().with_variant(JSONB, "postgresql"))  # array of tags
    followers_count = Column(Integer, default=0)  # number of followers

    created_at = Column(DateTime(timezone=True), index=True)
    updated_at = Column(DateTime(timezone=True))
    processed_at = Column(DateTime(timezone=True))  # set when state first becomes 'processed'
    enriched_at = Column(DateTime(timezone=True))  # when full details were fetched
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), index=True)  # soft delete timestamp

    # Foreign keys
    owner_id = Column(Integer, ForeignKey("members.id"), index=True)
    created_by_id = Column(Integer, ForeignKey("members.id"), index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    company_pb_id = Column(String, index=True)  # Store PB ID for relinking

    # Relationships
    owner = relationship("Member", foreign_keys=[owner_id])
    created_by = relationship("Member", foreign_keys=[created_by_id])
    company = relationship("Company")
    features = relationship("Feature", secondary="note_features", back_populates="notes")
    comments = relationship("NoteComment", back_populates="note", order_by="desc(NoteComment.timestamp)")
