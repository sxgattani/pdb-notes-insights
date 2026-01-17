from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    pb_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    domain = Column(String)

    # Custom fields
    customer_id = Column(String)  # Internal customer ID
    account_sales_theatre = Column(String, index=True)
    cse = Column(String)  # Customer Success Engineer
    arr = Column(Numeric(12, 2))  # Annual Recurring Revenue
    account_type = Column(String)
    contract_start_date = Column(Date)
    contract_end_date = Column(Date)

    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    customers = relationship("Customer", back_populates="company")
