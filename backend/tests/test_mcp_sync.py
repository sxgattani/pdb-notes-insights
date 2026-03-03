import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import SyncHistory
from notes_mcp.tools.sync import _get_sync_status_impl, _get_sync_history_impl


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_sync_status_idle_when_no_history(db):
    result = _get_sync_status_impl(db)
    assert result["status"] == "idle"
    assert result["last_sync_at"] is None


def test_sync_status_shows_last_sync(db):
    h = SyncHistory(entity_type="all", status="completed",
                    started_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
                    completed_at=datetime(2025, 1, 1, 0, 5, tzinfo=timezone.utc),
                    records_synced=42)
    db.add(h)
    db.commit()
    result = _get_sync_status_impl(db)
    assert result["status"] == "idle"
    assert result["last_sync_at"] is not None
    assert result["last_records_synced"] == 42


def test_sync_status_running(db):
    h = SyncHistory(entity_type="notes", status="running",
                    started_at=datetime(2025, 1, 1, tzinfo=timezone.utc))
    db.add(h)
    db.commit()
    result = _get_sync_status_impl(db)
    assert result["status"] == "running"


def test_sync_history_returns_records(db):
    for i in range(3):
        db.add(SyncHistory(entity_type="all", status="completed",
                           started_at=datetime(2025, 1, i + 1, tzinfo=timezone.utc),
                           completed_at=datetime(2025, 1, i + 1, 0, 5, tzinfo=timezone.utc),
                           records_synced=10))
    db.commit()
    result = _get_sync_history_impl(db, limit=2)
    assert len(result) == 2
