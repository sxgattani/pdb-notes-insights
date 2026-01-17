import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import User, Team, Company, Customer, Component, Feature
from decimal import Decimal
from datetime import date


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


def test_company_model_create(db_session):
    company = Company(
        pb_id="pb_company_789",
        name="Acme Corp",
        domain="acme.com",
        customer_id="CUST-001",
        account_sales_theatre="EMEA",
        cse="Bob Smith",
        arr=Decimal("150000.00"),
        account_type="Enterprise",
        contract_start_date=date(2024, 1, 1),
        contract_end_date=date(2025, 1, 1),
    )
    db_session.add(company)
    db_session.commit()

    result = db_session.query(Company).filter_by(pb_id="pb_company_789").first()
    assert result is not None
    assert result.name == "Acme Corp"
    assert result.arr == Decimal("150000.00")
    assert result.account_sales_theatre == "EMEA"


def test_customer_model_with_company(db_session):
    company = Company(pb_id="pb_company_999", name="Test Corp")
    db_session.add(company)
    db_session.commit()

    customer = Customer(
        pb_id="pb_customer_111",
        name="Jane Doe",
        email="jane@testcorp.com",
        company_id=company.id,
    )
    db_session.add(customer)
    db_session.commit()

    result = db_session.query(Customer).filter_by(pb_id="pb_customer_111").first()
    assert result is not None
    assert result.name == "Jane Doe"
    assert result.company.name == "Test Corp"


def test_component_model_with_hierarchy(db_session):
    parent = Component(pb_id="pb_comp_parent", name="Platform")
    db_session.add(parent)
    db_session.commit()

    child = Component(pb_id="pb_comp_child", name="API", parent_id=parent.id)
    db_session.add(child)
    db_session.commit()

    result = db_session.query(Component).filter_by(pb_id="pb_comp_child").first()
    assert result is not None
    assert result.name == "API"
    assert result.parent.name == "Platform"


def test_feature_model_create(db_session):
    user = User(pb_id="pb_user_pm", name="PM Alice")
    team = Team(pb_id="pb_team_platform", name="Platform")
    db_session.add_all([user, team])
    db_session.commit()

    feature = Feature(
        pb_id="pb_feature_123",
        name="User Authentication",
        description="Add OAuth support",
        type="feature",
        status="in_progress",
        owner_id=user.id,
        team_id=team.id,
        product_area="Security",
        product_area_stack_rank=1,
        committed=True,
        risk="low",
        custom_fields={"priority": "high"},
    )
    db_session.add(feature)
    db_session.commit()

    result = db_session.query(Feature).filter_by(pb_id="pb_feature_123").first()
    assert result is not None
    assert result.name == "User Authentication"
    assert result.product_area == "Security"
    assert result.committed is True
    assert result.custom_fields["priority"] == "high"
    assert result.owner.name == "PM Alice"
