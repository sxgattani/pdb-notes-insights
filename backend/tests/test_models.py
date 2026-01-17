import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import User, Team


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_user_model_create(db_session):
    user = User(pb_id="pb_user_123", name="Alice", email="alice@example.com", role="pm")
    db_session.add(user)
    db_session.commit()

    result = db_session.query(User).filter_by(pb_id="pb_user_123").first()
    assert result is not None
    assert result.name == "Alice"
    assert result.email == "alice@example.com"


def test_team_model_create(db_session):
    team = Team(pb_id="pb_team_456", name="Platform Team")
    db_session.add(team)
    db_session.commit()

    result = db_session.query(Team).filter_by(pb_id="pb_team_456").first()
    assert result is not None
    assert result.name == "Platform Team"
