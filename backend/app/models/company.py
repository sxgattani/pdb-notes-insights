from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric
from sqlalchemy.sql import func

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    pb_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, index=True)
    domain = Column(String)

    # Custom fields from ProductBoard
    customer_id = Column(String)  # Internal customer ID
    account_sales_theatre = Column(String, index=True)
    cse = Column(String)  # Customer Success Engineer
    arr = Column(Numeric(12, 2), index=True)  # Annual Recurring Revenue
    account_type = Column(String, index=True)
    contract_start_date = Column(Date)
    contract_end_date = Column(Date)

    synced_at = Column(DateTime(timezone=True), server_default=func.now())
