import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import User, SyncHistory, Note
from app.services.sync.users_syncer import UsersSyncer
from app.services.sync.notes_syncer import NotesSyncer


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.mark.asyncio
async def test_users_syncer_creates_sync_history(db_session):
    syncer = UsersSyncer(db_session)

    mock_users = [
        {"id": "pb_u1", "name": "Alice", "email": "alice@test.com", "role": "admin"},
        {"id": "pb_u2", "name": "Bob", "email": "bob@test.com", "role": "member"},
    ]

    with patch("app.services.sync.users_syncer.ProductBoardClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        with patch("app.services.sync.users_syncer.UsersAPI") as mock_api:
            mock_api_instance = MagicMock()
            mock_api_instance.list_users = AsyncMock(return_value=mock_users)
            mock_api.return_value = mock_api_instance

            count = await syncer.sync()

    assert count == 2

    # Verify users created
    users = db_session.query(User).all()
    assert len(users) == 2

    # Verify sync history
    history = db_session.query(SyncHistory).first()
    assert history.entity_type == "users"
    assert history.status == "completed"
    assert history.records_synced == 2


@pytest.mark.asyncio
async def test_notes_syncer_upserts_notes(db_session):
    syncer = NotesSyncer(db_session)

    mock_notes = [
        {
            "id": "pb_note_1",
            "title": "Feature Request",
            "content": "Please add dark mode",
            "type": "simple",
            "source": "intercom",
            "state": "unprocessed",
            "createdAt": "2024-01-15T10:00:00Z",
        },
    ]

    with patch("app.services.sync.notes_syncer.ProductBoardClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        with patch("app.services.sync.notes_syncer.NotesAPI") as mock_api:
            mock_api_instance = MagicMock()
            mock_api_instance.list_notes = AsyncMock(return_value=mock_notes)
            mock_api.return_value = mock_api_instance

            count = await syncer.sync()

    assert count == 1

    note = db_session.query(Note).first()
    assert note.title == "Feature Request"
    assert note.state == "unprocessed"
