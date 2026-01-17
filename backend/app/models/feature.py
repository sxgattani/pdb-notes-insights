from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class Feature(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, index=True)
    pb_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    description = Column(String)
    type = Column(String)  # feature, subfeature
    status = Column(String)
    component_id = Column(Integer, ForeignKey("components.id"), index=True)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    creator_id = Column(Integer, ForeignKey("users.id"), index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), index=True)

    # Custom fields (known)
    product_area = Column(String, index=True)
    product_area_stack_rank = Column(Integer)
    committed = Column(Boolean)
    risk = Column(String)
    tech_lead_id = Column(Integer, ForeignKey("users.id"), index=True)

    # Extensibility
    custom_fields = Column(JSON().with_variant(JSONB, "postgresql"))

    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    component = relationship("Component")
    creator = relationship("User", foreign_keys=[creator_id])
    owner = relationship("User", foreign_keys=[owner_id])
    team = relationship("Team")
    tech_lead = relationship("User", foreign_keys=[tech_lead_id])
