from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Component(Base):
    __tablename__ = "components"

    id = Column(Integer, primary_key=True, index=True)
    pb_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    parent_id = Column(Integer, ForeignKey("components.id"), index=True)
    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    # Self-referential relationship
    parent = relationship("Component", remote_side=[id], backref="children")
