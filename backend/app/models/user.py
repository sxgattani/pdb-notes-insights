from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    pb_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    email = Column(String)
    role = Column(String)
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
