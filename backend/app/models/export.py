from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func

from app.database import Base


class Export(Base):
    __tablename__ = "exports"

    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String, nullable=False)  # notes_summary, features_summary, pm_performance, sla_report
    format = Column(String, nullable=False)  # pdf, json
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer)  # bytes
    status = Column(String, default="pending")  # pending, generating, completed, failed
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    # Optional: who triggered it
    triggered_by = Column(String)  # "scheduler" or "manual"
