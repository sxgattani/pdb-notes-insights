import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Note, Member, Company
from mcp.tools.reports import (
    _get_notes_insights_impl,
    _get_notes_trend_impl,
    _get_response_time_stats_impl,
    _get_sla_report_impl,
    _get_pm_workload_impl,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_data(db):
    now = datetime.utcnow()
    member = Member(id=1, email="pm@example.com", name="Alice PM", pb_id="m-1")
    company = Company(id=1, pb_id="c-1", name="Acme Corp")
    # Recent note, processed quickly (1 day)
    n1 = Note(id=1, pb_id="n-1", title="Note 1", state="processed",
               created_at=now - timedelta(days=10), processed_at=now - timedelta(days=9),
               owner_id=1, company_id=1)
    # Recent note, unprocessed, SLA breached (8 days old)
    n2 = Note(id=2, pb_id="n-2", title="Note 2", state="unprocessed",
               created_at=now - timedelta(days=8), owner_id=1, company_id=1)
    # Recent note, unprocessed, on track (2 days old)
    n3 = Note(id=3, pb_id="n-3", title="Note 3", state="unprocessed",
               created_at=now - timedelta(days=2), owner_id=1)
    db.add_all([member, company, n1, n2, n3])
    db.commit()
    return db


def test_notes_insights_summary(sample_data):
    result = _get_notes_insights_impl(sample_data, days=90)
    assert result["summary"]["created"]["value"] == 3
    assert result["summary"]["processed"]["value"] == 1
    assert result["summary"]["unprocessed"]["value"] == 2


def test_notes_insights_by_owner(sample_data):
    result = _get_notes_insights_impl(sample_data, days=90)
    owners = result["by_owner"]
    assert len(owners) >= 1
    alice = next(o for o in owners if o["name"] == "Alice PM")
    assert alice["assigned"] == 3
    assert alice["processed"] == 1


def test_notes_trend_returns_weeks(sample_data):
    result = _get_notes_trend_impl(sample_data, days=90)
    assert len(result["data"]) > 0
    assert "week" in result["data"][0]
    assert "created" in result["data"][0]


def test_response_time_stats(sample_data):
    result = _get_response_time_stats_impl(sample_data, days=90)
    assert result["average_days"] == 1.0
    assert len(result["distribution"]) == 4


def test_sla_report_breached(sample_data):
    result = _get_sla_report_impl(sample_data)
    assert result["summary"]["breached"] == 1  # 8-day-old note breaches 5-day SLA
    assert result["summary"]["on_track"] == 1  # 2-day-old note


def test_pm_workload(sample_data):
    result = _get_pm_workload_impl(sample_data)
    assert result["summary"]["total_unprocessed"] == 2
    alice = next(w for w in result["data"] if w["name"] == "Alice PM")
    assert alice["unprocessed_notes"] == 2


def test_soft_deleted_note_excluded_from_insights(sample_data):
    """Soft-deleted notes must not appear in insights counts."""
    from datetime import datetime
    deleted = Note(
        id=99, pb_id="n-99", title="Deleted", state="unprocessed",
        created_at=datetime.utcnow() - timedelta(days=5),
        deleted_at=datetime.utcnow(),
        owner_id=1,
    )
    sample_data.add(deleted)
    sample_data.commit()
    result = _get_notes_insights_impl(sample_data, days=90)
    # Still 3 notes, not 4
    assert result["summary"]["created"]["value"] == 3


def test_sla_at_risk_note(db):
    """Notes 4-5 days old should appear in at_risk, not breached or on_track."""
    note = Note(
        id=50, pb_id="n-50", title="At risk", state="unprocessed",
        created_at=datetime.utcnow() - timedelta(days=4, hours=12),
    )
    db.add(note)
    db.commit()
    result = _get_sla_report_impl(db)
    assert result["summary"]["at_risk"] == 1
    assert result["summary"]["breached"] == 0


def test_insights_days_filter(db):
    """Notes older than the days window should be excluded."""
    old_note = Note(
        id=60, pb_id="n-60", title="Old note", state="unprocessed",
        created_at=datetime.utcnow() - timedelta(days=100),
    )
    recent_note = Note(
        id=61, pb_id="n-61", title="Recent note", state="unprocessed",
        created_at=datetime.utcnow() - timedelta(days=10),
    )
    db.add_all([old_note, recent_note])
    db.commit()
    result = _get_notes_insights_impl(db, days=90)
    assert result["summary"]["created"]["value"] == 1  # only recent note
