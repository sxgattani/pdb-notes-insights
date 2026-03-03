import json
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Note, Member, Company, Feature, NoteFeature
from mcp.tools.notes import (
    _list_notes_impl,
    _get_note_impl,
    _search_notes_impl,
    _get_notes_stats_impl,
    _list_members_impl,
    _list_companies_impl,
    _list_features_impl,
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
    member = Member(id=1, email="pm@example.com", name="Alice PM", pb_id="m-1")
    company = Company(id=1, pb_id="c-1", name="Acme Corp")
    feature = Feature(id=1, pb_id="f-1", name="Dark Mode", display_url="https://pb.com/f-1")
    note1 = Note(
        id=1, pb_id="n-1", title="Login bug", content="Users cannot login",
        state="unprocessed", source_origin="feature_request",
        created_at=datetime(2025, 1, 10), owner_id=1, company_id=1,
    )
    note2 = Note(
        id=2, pb_id="n-2", title="Dark mode request", content="Please add dark mode",
        state="processed", source_origin="feature_request",
        created_at=datetime(2025, 1, 15), processed_at=datetime(2025, 1, 18),
        owner_id=1, company_id=1,
    )
    db.add_all([member, company, feature, note1, note2])
    db.add(NoteFeature(note_id=2, feature_id=1, importance="high"))
    db.commit()
    return db


def test_list_notes_returns_all(sample_data):
    result = _list_notes_impl(sample_data)
    assert result["pagination"]["total"] == 2
    assert len(result["data"]) == 2


def test_list_notes_filters_by_state(sample_data):
    result = _list_notes_impl(sample_data, state="unprocessed")
    assert result["pagination"]["total"] == 1
    assert result["data"][0]["state"] == "unprocessed"


def test_list_notes_group_by_owner(sample_data):
    result = _list_notes_impl(sample_data, group_by="owner")
    assert result["group_counts"] is not None
    assert "Alice PM" in result["group_counts"]


def test_get_note_returns_details(sample_data):
    result = _get_note_impl(sample_data, note_id=2)
    assert result["title"] == "Dark mode request"
    assert len(result["features"]) == 1
    assert result["features"][0]["name"] == "Dark Mode"


def test_get_note_not_found(sample_data):
    result = _get_note_impl(sample_data, note_id=999)
    assert result is None


def test_search_notes_finds_by_title(sample_data):
    result = _search_notes_impl(sample_data, query="dark")
    assert result["pagination"]["total"] == 1
    assert result["data"][0]["title"] == "Dark mode request"


def test_search_notes_finds_by_content(sample_data):
    result = _search_notes_impl(sample_data, query="cannot login")
    assert result["pagination"]["total"] == 1


def test_get_notes_stats(sample_data):
    result = _get_notes_stats_impl(sample_data)
    assert result["total"] == 2
    assert result["processed"] == 1
    assert result["unprocessed"] == 1


def test_list_members(sample_data):
    result = _list_members_impl(sample_data)
    assert len(result) == 1
    assert result[0]["name"] == "Alice PM"


def test_list_companies(sample_data):
    result = _list_companies_impl(sample_data)
    assert len(result) == 1
    assert result[0]["name"] == "Acme Corp"


def test_list_features(sample_data):
    result = _list_features_impl(sample_data)
    assert len(result) == 1
    assert result[0]["name"] == "Dark Mode"
    assert result[0]["note_count"] == 1
