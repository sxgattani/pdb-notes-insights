from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Member(Base):
    """ProductBoard member - can be an owner, creator, or commenter."""
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    pb_id = Column(String, unique=True, nullable=True, index=True)  # nullable - owners don't have IDs
    email = Column(String, unique=True, nullable=False, index=True)  # primary lookup key
    name = Column(String)
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
