from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class FeatureCustomer(Base):
    __tablename__ = "feature_customers"

    feature_id = Column(Integer, ForeignKey("features.id", ondelete="CASCADE"), primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True)
    source = Column(String)  # direct, via_note, inferred
    note_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
