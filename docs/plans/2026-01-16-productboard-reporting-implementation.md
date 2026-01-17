# ProductBoard Reporting System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a read-only reporting system for ProductBoard notes with a web dashboard, SLA tracking, and scheduled exports.

**Architecture:** FastAPI backend syncs data from ProductBoard API to PostgreSQL, exposes REST endpoints. React frontend renders dashboards with drill-down. APScheduler handles periodic sync and nightly exports.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, Alembic, APScheduler, httpx, WeasyPrint | React 18, TypeScript, Recharts, TanStack Table/Query, Tailwind CSS | PostgreSQL 15, Docker Compose

---

## Phase 1: Project Setup & Infrastructure

### Task 1.1: Initialize Backend Project

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`
- Create: `.env.example`

**Step 1: Create backend directory structure**

```bash
mkdir -p backend/app
```

**Step 2: Create requirements.txt**

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9
httpx==0.26.0
apscheduler==3.10.4
python-dotenv==1.0.0
pydantic-settings==2.1.0
weasyprint==60.2
python-multipart==0.0.6
passlib[bcrypt]==1.7.4
```

**Step 3: Create config.py**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/pdb_insights"

    # ProductBoard API
    productboard_api_token: str = ""
    productboard_api_url: str = "https://api.productboard.com"

    # Auth
    auth_username: str = "admin"
    auth_password: str = "changeme"
    session_secret: str = "change-this-secret-key"

    # Sync
    sync_interval_hours: int = 4
    sync_enabled: bool = True

    # Exports
    export_schedule_hour: int = 2
    export_retention_days: int = 30
    export_path: str = "./exports"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**Step 4: Create main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="ProductBoard Insights",
    description="Read-only reporting system for ProductBoard notes",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

**Step 5: Create __init__.py**

```python
# backend/app/__init__.py
```

**Step 6: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 7: Create .env.example**

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/pdb_insights

# ProductBoard API
PRODUCTBOARD_API_TOKEN=your_api_token_here
PRODUCTBOARD_API_URL=https://api.productboard.com

# Auth
AUTH_USERNAME=admin
AUTH_PASSWORD=changeme
SESSION_SECRET=change-this-secret-key

# Sync
SYNC_INTERVAL_HOURS=4
SYNC_ENABLED=true

# Exports
EXPORT_SCHEDULE_HOUR=2
EXPORT_RETENTION_DAYS=30
EXPORT_PATH=./exports
```

**Step 8: Test backend starts**

```bash
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
```

Expected: Server starts on http://127.0.0.1:8000

**Step 9: Verify health endpoint**

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"healthy"}`

**Step 10: Commit**

```bash
git add backend/ .env.example
git commit -m "feat: initialize backend project with FastAPI"
```

---

### Task 1.2: Set Up Database Connection

**Files:**
- Create: `backend/app/database.py`

**Step 1: Create database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 2: Commit**

```bash
git add backend/app/database.py
git commit -m "feat: add database connection setup"
```

---

### Task 1.3: Set Up Alembic Migrations

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/` (directory)

**Step 1: Initialize alembic**

```bash
cd backend && alembic init alembic
```

**Step 2: Update alembic/env.py**

Replace the content with:

```python
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.config import get_settings
from app.database import Base

# Import all models here so they're registered with Base
# from app.models import note, feature, customer, company, user, team, component

config = context.config

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Step 3: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat: configure alembic for database migrations"
```

---

### Task 1.4: Create Docker Compose

**Files:**
- Create: `docker-compose.yml`

**Step 1: Create docker-compose.yml**

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/pdb_insights
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend:/app
      - ./exports:/app/exports
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: pdb_insights
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

**Step 2: Create .env file from example**

```bash
cp .env.example .env
```

**Step 3: Start database**

```bash
docker-compose up -d db
```

Expected: PostgreSQL container running on port 5432

**Step 4: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add docker-compose for local development"
```

---

## Phase 2: Database Models

### Task 2.1: Create User and Team Models

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/team.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_models.py`

**Step 1: Create models directory**

```bash
mkdir -p backend/app/models backend/tests
```

**Step 2: Create models/__init__.py**

```python
from app.models.user import User
from app.models.team import Team

__all__ = ["User", "Team"]
```

**Step 3: Create user.py**

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    pb_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    email = Column(String)
    role = Column(String)
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Step 4: Create team.py**

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    pb_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Step 5: Create tests/__init__.py**

```python
# backend/tests/__init__.py
```

**Step 6: Create test_models.py**

```python
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
```

**Step 7: Add pytest to requirements.txt**

Add to `backend/requirements.txt`:
```
pytest==7.4.4
```

**Step 8: Run tests**

```bash
cd backend && pip install pytest && pytest tests/test_models.py -v
```

Expected: 2 tests pass

**Step 9: Commit**

```bash
git add backend/app/models/ backend/tests/ backend/requirements.txt
git commit -m "feat: add User and Team models with tests"
```

---

### Task 2.2: Create Company and Customer Models

**Files:**
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/models/company.py`
- Create: `backend/app/models/customer.py`
- Modify: `backend/tests/test_models.py`

**Step 1: Create company.py**

```python
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
```

**Step 2: Create customer.py**

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    pb_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    email = Column(String)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    created_at = Column(DateTime(timezone=True))
    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    company = relationship("Company", back_populates="customers")
```

**Step 3: Update models/__init__.py**

```python
from app.models.user import User
from app.models.team import Team
from app.models.company import Company
from app.models.customer import Customer

__all__ = ["User", "Team", "Company", "Customer"]
```

**Step 4: Add tests to test_models.py**

Append to `backend/tests/test_models.py`:

```python
from app.models import Company, Customer
from decimal import Decimal
from datetime import date


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
```

**Step 5: Run tests**

```bash
cd backend && pytest tests/test_models.py -v
```

Expected: 4 tests pass

**Step 6: Commit**

```bash
git add backend/app/models/ backend/tests/test_models.py
git commit -m "feat: add Company and Customer models with tests"
```

---

### Task 2.3: Create Component Model

**Files:**
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/models/component.py`
- Modify: `backend/tests/test_models.py`

**Step 1: Create component.py**

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Component(Base):
    __tablename__ = "components"

    id = Column(Integer, primary_key=True, index=True)
    pb_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    parent_id = Column(Integer, ForeignKey("components.id"), index=True)
    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    # Self-referential relationship
    parent = relationship("Component", remote_side=[id], backref="children")
```

**Step 2: Update models/__init__.py**

```python
from app.models.user import User
from app.models.team import Team
from app.models.company import Company
from app.models.customer import Customer
from app.models.component import Component

__all__ = ["User", "Team", "Company", "Customer", "Component"]
```

**Step 3: Add test to test_models.py**

Append:

```python
from app.models import Component


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
```

**Step 4: Run tests**

```bash
cd backend && pytest tests/test_models.py -v
```

Expected: 5 tests pass

**Step 5: Commit**

```bash
git add backend/app/models/ backend/tests/test_models.py
git commit -m "feat: add Component model with self-referential hierarchy"
```

---

### Task 2.4: Create Feature Model

**Files:**
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/models/feature.py`
- Modify: `backend/tests/test_models.py`

**Step 1: Create feature.py**

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
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
    custom_fields = Column(JSONB)

    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    component = relationship("Component")
    creator = relationship("User", foreign_keys=[creator_id])
    owner = relationship("User", foreign_keys=[owner_id])
    team = relationship("Team")
    tech_lead = relationship("User", foreign_keys=[tech_lead_id])
```

**Step 2: Update models/__init__.py**

```python
from app.models.user import User
from app.models.team import Team
from app.models.company import Company
from app.models.customer import Customer
from app.models.component import Component
from app.models.feature import Feature

__all__ = ["User", "Team", "Company", "Customer", "Component", "Feature"]
```

**Step 3: Add test to test_models.py**

Append:

```python
from app.models import Feature


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
```

**Step 4: Run tests**

```bash
cd backend && pytest tests/test_models.py -v
```

Expected: 6 tests pass

**Step 5: Commit**

```bash
git add backend/app/models/ backend/tests/test_models.py
git commit -m "feat: add Feature model with custom fields"
```

---

### Task 2.5: Create Note Model

**Files:**
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/models/note.py`
- Modify: `backend/tests/test_models.py`

**Step 1: Create note.py**

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    pb_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String)
    content = Column(Text)
    type = Column(String)  # simple, conversation, opportunity
    source = Column(String)
    state = Column(String, index=True)  # processed, unprocessed
    processed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    creator_id = Column(Integer, ForeignKey("users.id"), index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)

    # Extensibility
    custom_fields = Column(JSONB)

    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    creator = relationship("User", foreign_keys=[creator_id])
    owner = relationship("User", foreign_keys=[owner_id])
    team = relationship("Team")
    customer = relationship("Customer")
```

**Step 2: Update models/__init__.py**

```python
from app.models.user import User
from app.models.team import Team
from app.models.company import Company
from app.models.customer import Customer
from app.models.component import Component
from app.models.feature import Feature
from app.models.note import Note

__all__ = ["User", "Team", "Company", "Customer", "Component", "Feature", "Note"]
```

**Step 3: Add test to test_models.py**

Append:

```python
from app.models import Note
from datetime import datetime, timezone


def test_note_model_create(db_session):
    user = User(pb_id="pb_user_owner", name="Note Owner")
    company = Company(pb_id="pb_company_note", name="Note Corp")
    db_session.add_all([user, company])
    db_session.commit()

    customer = Customer(pb_id="pb_cust_note", name="Customer", company_id=company.id)
    db_session.add(customer)
    db_session.commit()

    note = Note(
        pb_id="pb_note_456",
        title="Feature Request",
        content="Please add dark mode",
        type="simple",
        source="intercom",
        state="unprocessed",
        owner_id=user.id,
        customer_id=customer.id,
        created_at=datetime.now(timezone.utc),
        custom_fields={"sentiment": "positive"},
    )
    db_session.add(note)
    db_session.commit()

    result = db_session.query(Note).filter_by(pb_id="pb_note_456").first()
    assert result is not None
    assert result.title == "Feature Request"
    assert result.state == "unprocessed"
    assert result.customer.name == "Customer"
    assert result.owner.name == "Note Owner"
```

**Step 4: Run tests**

```bash
cd backend && pytest tests/test_models.py -v
```

Expected: 7 tests pass

**Step 5: Commit**

```bash
git add backend/app/models/ backend/tests/test_models.py
git commit -m "feat: add Note model with state tracking"
```

---

### Task 2.6: Create Junction Tables (NoteFeature, FeatureCustomer)

**Files:**
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/models/note_feature.py`
- Create: `backend/app/models/feature_customer.py`
- Modify: `backend/tests/test_models.py`

**Step 1: Create note_feature.py**

```python
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Table
from sqlalchemy.sql import func

from app.database import Base


class NoteFeature(Base):
    __tablename__ = "note_features"

    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    feature_id = Column(Integer, ForeignKey("features.id", ondelete="CASCADE"), primary_key=True)
    linked_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Step 2: Create feature_customer.py**

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class FeatureCustomer(Base):
    __tablename__ = "feature_customers"

    feature_id = Column(Integer, ForeignKey("features.id", ondelete="CASCADE"), primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True)
    source = Column(String)  # direct, via_note, inferred
    note_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Step 3: Update models/__init__.py**

```python
from app.models.user import User
from app.models.team import Team
from app.models.company import Company
from app.models.customer import Customer
from app.models.component import Component
from app.models.feature import Feature
from app.models.note import Note
from app.models.note_feature import NoteFeature
from app.models.feature_customer import FeatureCustomer

__all__ = [
    "User", "Team", "Company", "Customer", "Component",
    "Feature", "Note", "NoteFeature", "FeatureCustomer"
]
```

**Step 4: Add tests to test_models.py**

Append:

```python
from app.models import NoteFeature, FeatureCustomer


def test_note_feature_relationship(db_session):
    user = User(pb_id="pb_user_nf", name="User NF")
    db_session.add(user)
    db_session.commit()

    feature = Feature(pb_id="pb_feat_nf", name="Feature NF", owner_id=user.id)
    note = Note(pb_id="pb_note_nf", title="Note NF", owner_id=user.id)
    db_session.add_all([feature, note])
    db_session.commit()

    link = NoteFeature(note_id=note.id, feature_id=feature.id)
    db_session.add(link)
    db_session.commit()

    result = db_session.query(NoteFeature).filter_by(note_id=note.id).first()
    assert result is not None
    assert result.feature_id == feature.id


def test_feature_customer_relationship(db_session):
    company = Company(pb_id="pb_comp_fc", name="Company FC")
    db_session.add(company)
    db_session.commit()

    customer = Customer(pb_id="pb_cust_fc", name="Customer FC", company_id=company.id)
    user = User(pb_id="pb_user_fc", name="User FC")
    db_session.add_all([customer, user])
    db_session.commit()

    feature = Feature(pb_id="pb_feat_fc", name="Feature FC", owner_id=user.id)
    db_session.add(feature)
    db_session.commit()

    link = FeatureCustomer(
        feature_id=feature.id,
        customer_id=customer.id,
        source="via_note",
        note_count=5,
    )
    db_session.add(link)
    db_session.commit()

    result = db_session.query(FeatureCustomer).filter_by(feature_id=feature.id).first()
    assert result is not None
    assert result.customer_id == customer.id
    assert result.source == "via_note"
    assert result.note_count == 5
```

**Step 5: Run tests**

```bash
cd backend && pytest tests/test_models.py -v
```

Expected: 9 tests pass

**Step 6: Commit**

```bash
git add backend/app/models/ backend/tests/test_models.py
git commit -m "feat: add NoteFeature and FeatureCustomer junction tables"
```

---

### Task 2.7: Create SyncHistory Model

**Files:**
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/models/sync_history.py`
- Modify: `backend/tests/test_models.py`

**Step 1: Create sync_history.py**

```python
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func

from app.database import Base


class SyncHistory(Base):
    __tablename__ = "sync_history"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, index=True)  # notes, features, customers, etc.
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    status = Column(String)  # running, completed, partial, failed
    records_synced = Column(Integer, default=0)
    error_message = Column(Text)
```

**Step 2: Update models/__init__.py**

```python
from app.models.user import User
from app.models.team import Team
from app.models.company import Company
from app.models.customer import Customer
from app.models.component import Component
from app.models.feature import Feature
from app.models.note import Note
from app.models.note_feature import NoteFeature
from app.models.feature_customer import FeatureCustomer
from app.models.sync_history import SyncHistory

__all__ = [
    "User", "Team", "Company", "Customer", "Component",
    "Feature", "Note", "NoteFeature", "FeatureCustomer", "SyncHistory"
]
```

**Step 3: Add test**

Append to `backend/tests/test_models.py`:

```python
from app.models import SyncHistory


def test_sync_history_model(db_session):
    sync = SyncHistory(
        entity_type="notes",
        status="running",
    )
    db_session.add(sync)
    db_session.commit()

    result = db_session.query(SyncHistory).filter_by(entity_type="notes").first()
    assert result is not None
    assert result.status == "running"
    assert result.started_at is not None
```

**Step 4: Run tests**

```bash
cd backend && pytest tests/test_models.py -v
```

Expected: 10 tests pass

**Step 5: Commit**

```bash
git add backend/app/models/ backend/tests/test_models.py
git commit -m "feat: add SyncHistory model for tracking sync runs"
```

---

### Task 2.8: Create and Run Initial Migration

**Files:**
- Modify: `backend/alembic/env.py`
- Create: `backend/alembic/versions/001_initial_schema.py` (auto-generated)

**Step 1: Update alembic/env.py to import all models**

Update the imports section:

```python
from app.config import get_settings
from app.database import Base
from app.models import (
    User, Team, Company, Customer, Component,
    Feature, Note, NoteFeature, FeatureCustomer, SyncHistory
)
```

**Step 2: Generate migration**

```bash
cd backend && alembic revision --autogenerate -m "initial schema"
```

Expected: Migration file created in `alembic/versions/`

**Step 3: Run migration**

```bash
cd backend && alembic upgrade head
```

Expected: All tables created

**Step 4: Verify tables exist**

```bash
docker-compose exec db psql -U postgres -d pdb_insights -c "\dt"
```

Expected: List of 10+ tables including notes, features, customers, etc.

**Step 5: Commit**

```bash
git add backend/alembic/
git commit -m "feat: create initial database migration"
```

---

## Phase 3: ProductBoard API Client

### Task 3.1: Create Base API Client

**Files:**
- Create: `backend/app/integrations/__init__.py`
- Create: `backend/app/integrations/productboard/__init__.py`
- Create: `backend/app/integrations/productboard/client.py`
- Create: `backend/tests/test_productboard_client.py`

**Step 1: Create directory structure**

```bash
mkdir -p backend/app/integrations/productboard
```

**Step 2: Create integrations/__init__.py**

```python
# backend/app/integrations/__init__.py
```

**Step 3: Create productboard/__init__.py**

```python
from app.integrations.productboard.client import ProductBoardClient

__all__ = ["ProductBoardClient"]
```

**Step 4: Create client.py**

```python
import httpx
from typing import Any, Optional
import asyncio
from datetime import datetime

from app.config import get_settings


class RateLimiter:
    """Token bucket rate limiter for 40 req/sec (under 50 limit)."""

    def __init__(self, rate: float = 40.0):
        self.rate = rate
        self.tokens = rate
        self.last_update = datetime.now()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = datetime.now()
            elapsed = (now - self.last_update).total_seconds()
            self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


class ProductBoardClient:
    """Async client for ProductBoard API v2."""

    BASE_URL = "https://api.productboard.com"

    def __init__(self, api_token: Optional[str] = None):
        settings = get_settings()
        self.api_token = api_token or settings.productboard_api_token
        self.rate_limiter = RateLimiter()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "X-Version": "1",
        }

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=self.headers,
            timeout=30.0,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
        retries: int = 3,
    ) -> dict[str, Any]:
        """Make a rate-limited request with retries."""
        await self.rate_limiter.acquire()

        for attempt in range(retries):
            try:
                response = await self._client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json,
                )

                if response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = int(response.headers.get("Retry-After", 1))
                    await asyncio.sleep(wait_time)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        return {}

    async def get(self, path: str, params: Optional[dict] = None) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def get_paginated(
        self,
        path: str,
        params: Optional[dict] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch all pages of a paginated endpoint."""
        params = params or {}
        params["pageLimit"] = limit

        all_data = []

        while True:
            response = await self.get(path, params)
            data = response.get("data", [])
            all_data.extend(data)

            # Check for next page
            links = response.get("links", {})
            next_cursor = response.get("pageCursor")

            if not next_cursor or not data:
                break

            params["pageCursor"] = next_cursor

        return all_data
```

**Step 5: Create test file**

```python
# backend/tests/test_productboard_client.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.integrations.productboard.client import ProductBoardClient, RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_acquire():
    limiter = RateLimiter(rate=10.0)
    # Should not block for first few requests
    for _ in range(5):
        await limiter.acquire()
    assert limiter.tokens < 10


@pytest.mark.asyncio
async def test_client_headers():
    client = ProductBoardClient(api_token="test_token")
    assert client.headers["Authorization"] == "Bearer test_token"
    assert "X-Version" in client.headers


@pytest.mark.asyncio
async def test_client_context_manager():
    async with ProductBoardClient(api_token="test") as client:
        assert client._client is not None
```

**Step 6: Add pytest-asyncio to requirements.txt**

Add to `backend/requirements.txt`:
```
pytest-asyncio==0.23.3
```

**Step 7: Run tests**

```bash
cd backend && pip install pytest-asyncio && pytest tests/test_productboard_client.py -v
```

Expected: 3 tests pass

**Step 8: Commit**

```bash
git add backend/app/integrations/ backend/tests/test_productboard_client.py backend/requirements.txt
git commit -m "feat: add ProductBoard API client with rate limiting"
```

---

### Task 3.2: Add Notes API Methods

**Files:**
- Create: `backend/app/integrations/productboard/notes.py`
- Modify: `backend/app/integrations/productboard/__init__.py`

**Step 1: Create notes.py**

```python
from typing import Optional
from datetime import datetime

from app.integrations.productboard.client import ProductBoardClient


class NotesAPI:
    """ProductBoard Notes API methods."""

    def __init__(self, client: ProductBoardClient):
        self.client = client

    async def list_notes(
        self,
        updated_after: Optional[datetime] = None,
        state: Optional[str] = None,
    ) -> list[dict]:
        """Fetch all notes, optionally filtered."""
        params = {}

        if updated_after:
            params["updatedAfter"] = updated_after.isoformat()
        if state:
            params["state"] = state

        return await self.client.get_paginated("/notes", params)

    async def get_note(self, note_id: str) -> dict:
        """Fetch a single note by ID."""
        response = await self.client.get(f"/notes/{note_id}")
        return response.get("data", {})

    async def get_note_features(self, note_id: str) -> list[dict]:
        """Get features linked to a note."""
        return await self.client.get_paginated(f"/notes/{note_id}/features")
```

**Step 2: Update productboard/__init__.py**

```python
from app.integrations.productboard.client import ProductBoardClient
from app.integrations.productboard.notes import NotesAPI

__all__ = ["ProductBoardClient", "NotesAPI"]
```

**Step 3: Commit**

```bash
git add backend/app/integrations/productboard/
git commit -m "feat: add Notes API methods for ProductBoard"
```

---

### Task 3.3: Add Features API Methods

**Files:**
- Create: `backend/app/integrations/productboard/features.py`
- Modify: `backend/app/integrations/productboard/__init__.py`

**Step 1: Create features.py**

```python
from typing import Optional
from datetime import datetime

from app.integrations.productboard.client import ProductBoardClient


class FeaturesAPI:
    """ProductBoard Features API methods."""

    def __init__(self, client: ProductBoardClient):
        self.client = client

    async def list_features(
        self,
        updated_after: Optional[datetime] = None,
    ) -> list[dict]:
        """Fetch all features."""
        params = {}

        if updated_after:
            params["updatedAfter"] = updated_after.isoformat()

        return await self.client.get_paginated("/features", params)

    async def get_feature(self, feature_id: str) -> dict:
        """Fetch a single feature by ID."""
        response = await self.client.get(f"/features/{feature_id}")
        return response.get("data", {})

    async def get_feature_notes(self, feature_id: str) -> list[dict]:
        """Get notes linked to a feature."""
        return await self.client.get_paginated(f"/features/{feature_id}/notes")
```

**Step 2: Update productboard/__init__.py**

```python
from app.integrations.productboard.client import ProductBoardClient
from app.integrations.productboard.notes import NotesAPI
from app.integrations.productboard.features import FeaturesAPI

__all__ = ["ProductBoardClient", "NotesAPI", "FeaturesAPI"]
```

**Step 3: Commit**

```bash
git add backend/app/integrations/productboard/
git commit -m "feat: add Features API methods for ProductBoard"
```

---

### Task 3.4: Add Companies and Customers API Methods

**Files:**
- Create: `backend/app/integrations/productboard/companies.py`
- Create: `backend/app/integrations/productboard/customers.py`
- Modify: `backend/app/integrations/productboard/__init__.py`

**Step 1: Create companies.py**

```python
from typing import Optional
from datetime import datetime

from app.integrations.productboard.client import ProductBoardClient


class CompaniesAPI:
    """ProductBoard Companies API methods."""

    def __init__(self, client: ProductBoardClient):
        self.client = client

    async def list_companies(
        self,
        updated_after: Optional[datetime] = None,
    ) -> list[dict]:
        """Fetch all companies."""
        params = {}

        if updated_after:
            params["updatedAfter"] = updated_after.isoformat()

        return await self.client.get_paginated("/companies", params)

    async def get_company(self, company_id: str) -> dict:
        """Fetch a single company by ID."""
        response = await self.client.get(f"/companies/{company_id}")
        return response.get("data", {})
```

**Step 2: Create customers.py**

```python
from typing import Optional
from datetime import datetime

from app.integrations.productboard.client import ProductBoardClient


class CustomersAPI:
    """ProductBoard Customers API methods (called 'users' in PB API)."""

    def __init__(self, client: ProductBoardClient):
        self.client = client

    async def list_customers(
        self,
        updated_after: Optional[datetime] = None,
    ) -> list[dict]:
        """Fetch all customers (external users in ProductBoard)."""
        params = {}

        if updated_after:
            params["updatedAfter"] = updated_after.isoformat()

        # Note: ProductBoard calls these "customers" in some contexts
        return await self.client.get_paginated("/customers", params)

    async def get_customer(self, customer_id: str) -> dict:
        """Fetch a single customer by ID."""
        response = await self.client.get(f"/customers/{customer_id}")
        return response.get("data", {})
```

**Step 3: Update productboard/__init__.py**

```python
from app.integrations.productboard.client import ProductBoardClient
from app.integrations.productboard.notes import NotesAPI
from app.integrations.productboard.features import FeaturesAPI
from app.integrations.productboard.companies import CompaniesAPI
from app.integrations.productboard.customers import CustomersAPI

__all__ = [
    "ProductBoardClient", "NotesAPI", "FeaturesAPI",
    "CompaniesAPI", "CustomersAPI"
]
```

**Step 4: Commit**

```bash
git add backend/app/integrations/productboard/
git commit -m "feat: add Companies and Customers API methods"
```

---

### Task 3.5: Add Users and Components API Methods

**Files:**
- Create: `backend/app/integrations/productboard/users.py`
- Create: `backend/app/integrations/productboard/components.py`
- Modify: `backend/app/integrations/productboard/__init__.py`

**Step 1: Create users.py**

```python
from typing import Optional
from datetime import datetime

from app.integrations.productboard.client import ProductBoardClient


class UsersAPI:
    """ProductBoard Users API methods (internal team members)."""

    def __init__(self, client: ProductBoardClient):
        self.client = client

    async def list_users(self) -> list[dict]:
        """Fetch all workspace members."""
        return await self.client.get_paginated("/users")

    async def get_user(self, user_id: str) -> dict:
        """Fetch a single user by ID."""
        response = await self.client.get(f"/users/{user_id}")
        return response.get("data", {})
```

**Step 2: Create components.py**

```python
from typing import Optional

from app.integrations.productboard.client import ProductBoardClient


class ComponentsAPI:
    """ProductBoard Components API methods."""

    def __init__(self, client: ProductBoardClient):
        self.client = client

    async def list_components(self) -> list[dict]:
        """Fetch all components (product hierarchy)."""
        return await self.client.get_paginated("/components")

    async def get_component(self, component_id: str) -> dict:
        """Fetch a single component by ID."""
        response = await self.client.get(f"/components/{component_id}")
        return response.get("data", {})
```

**Step 3: Update productboard/__init__.py**

```python
from app.integrations.productboard.client import ProductBoardClient
from app.integrations.productboard.notes import NotesAPI
from app.integrations.productboard.features import FeaturesAPI
from app.integrations.productboard.companies import CompaniesAPI
from app.integrations.productboard.customers import CustomersAPI
from app.integrations.productboard.users import UsersAPI
from app.integrations.productboard.components import ComponentsAPI

__all__ = [
    "ProductBoardClient", "NotesAPI", "FeaturesAPI",
    "CompaniesAPI", "CustomersAPI", "UsersAPI", "ComponentsAPI"
]
```

**Step 4: Commit**

```bash
git add backend/app/integrations/productboard/
git commit -m "feat: add Users and Components API methods"
```

---

## Phase 4: Sync Engine

### Task 4.1: Create Sync Service Base

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/sync/__init__.py`
- Create: `backend/app/services/sync/base.py`

**Step 1: Create directory structure**

```bash
mkdir -p backend/app/services/sync
```

**Step 2: Create services/__init__.py**

```python
# backend/app/services/__init__.py
```

**Step 3: Create sync/__init__.py**

```python
# backend/app/services/sync/__init__.py
```

**Step 4: Create base.py**

```python
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, TypeVar, Generic
from sqlalchemy.orm import Session

from app.models import SyncHistory

T = TypeVar("T")


class BaseSyncer(ABC, Generic[T]):
    """Base class for entity syncers."""

    entity_type: str = ""

    def __init__(self, db: Session):
        self.db = db
        self.sync_history: Optional[SyncHistory] = None

    def start_sync(self) -> SyncHistory:
        """Record sync start."""
        self.sync_history = SyncHistory(
            entity_type=self.entity_type,
            status="running",
        )
        self.db.add(self.sync_history)
        self.db.commit()
        return self.sync_history

    def complete_sync(self, records_synced: int):
        """Record sync completion."""
        if self.sync_history:
            self.sync_history.status = "completed"
            self.sync_history.completed_at = datetime.utcnow()
            self.sync_history.records_synced = records_synced
            self.db.commit()

    def fail_sync(self, error_message: str):
        """Record sync failure."""
        if self.sync_history:
            self.sync_history.status = "failed"
            self.sync_history.completed_at = datetime.utcnow()
            self.sync_history.error_message = error_message
            self.db.commit()

    def get_last_sync_time(self) -> Optional[datetime]:
        """Get the last successful sync time for this entity type."""
        last_sync = (
            self.db.query(SyncHistory)
            .filter(
                SyncHistory.entity_type == self.entity_type,
                SyncHistory.status == "completed",
            )
            .order_by(SyncHistory.completed_at.desc())
            .first()
        )
        return last_sync.completed_at if last_sync else None

    @abstractmethod
    async def sync(self) -> int:
        """Perform the sync. Returns number of records synced."""
        pass
```

**Step 5: Commit**

```bash
git add backend/app/services/
git commit -m "feat: add base syncer class for sync engine"
```

---

### Task 4.2: Create Users Syncer

**Files:**
- Create: `backend/app/services/sync/users_syncer.py`
- Create: `backend/tests/test_sync.py`

**Step 1: Create users_syncer.py**

```python
from sqlalchemy.orm import Session

from app.services.sync.base import BaseSyncer
from app.models import User
from app.integrations.productboard import ProductBoardClient, UsersAPI


class UsersSyncer(BaseSyncer[User]):
    """Syncs users from ProductBoard."""

    entity_type = "users"

    async def sync(self) -> int:
        """Sync all users from ProductBoard."""
        self.start_sync()

        try:
            async with ProductBoardClient() as client:
                api = UsersAPI(client)
                pb_users = await api.list_users()

            count = 0
            for pb_user in pb_users:
                self._upsert_user(pb_user)
                count += 1

            self.db.commit()
            self.complete_sync(count)
            return count

        except Exception as e:
            self.fail_sync(str(e))
            raise

    def _upsert_user(self, pb_user: dict):
        """Insert or update a user."""
        pb_id = pb_user.get("id")

        user = self.db.query(User).filter(User.pb_id == pb_id).first()

        if not user:
            user = User(pb_id=pb_id)
            self.db.add(user)

        user.name = pb_user.get("name")
        user.email = pb_user.get("email")
        user.role = pb_user.get("role")
```

**Step 2: Create test_sync.py**

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import User, SyncHistory
from app.services.sync.users_syncer import UsersSyncer


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
```

**Step 3: Run tests**

```bash
cd backend && pytest tests/test_sync.py -v
```

Expected: 1 test passes

**Step 4: Commit**

```bash
git add backend/app/services/sync/ backend/tests/test_sync.py
git commit -m "feat: add Users syncer with tests"
```

---

### Task 4.3: Create Notes Syncer

**Files:**
- Create: `backend/app/services/sync/notes_syncer.py`
- Modify: `backend/tests/test_sync.py`

**Step 1: Create notes_syncer.py**

```python
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.services.sync.base import BaseSyncer
from app.models import Note, User, Team, Customer
from app.integrations.productboard import ProductBoardClient, NotesAPI


class NotesSyncer(BaseSyncer[Note]):
    """Syncs notes from ProductBoard."""

    entity_type = "notes"

    async def sync(self) -> int:
        """Sync notes from ProductBoard (incremental)."""
        self.start_sync()
        last_sync = self.get_last_sync_time()

        try:
            async with ProductBoardClient() as client:
                api = NotesAPI(client)
                pb_notes = await api.list_notes(updated_after=last_sync)

            count = 0
            for pb_note in pb_notes:
                self._upsert_note(pb_note)
                count += 1

            self.db.commit()
            self.complete_sync(count)
            return count

        except Exception as e:
            self.fail_sync(str(e))
            raise

    def _upsert_note(self, pb_note: dict):
        """Insert or update a note."""
        pb_id = pb_note.get("id")

        note = self.db.query(Note).filter(Note.pb_id == pb_id).first()

        if not note:
            note = Note(pb_id=pb_id)
            self.db.add(note)

        note.title = pb_note.get("title")
        note.content = pb_note.get("content")
        note.type = pb_note.get("type")
        note.source = pb_note.get("source")
        note.state = pb_note.get("state", "unprocessed")

        # Parse dates
        if pb_note.get("createdAt"):
            note.created_at = datetime.fromisoformat(
                pb_note["createdAt"].replace("Z", "+00:00")
            )
        if pb_note.get("updatedAt"):
            note.updated_at = datetime.fromisoformat(
                pb_note["updatedAt"].replace("Z", "+00:00")
            )

        # Handle state change for processed_at
        if note.state == "processed" and not note.processed_at:
            note.processed_at = datetime.utcnow()

        # Resolve owner
        owner_data = pb_note.get("owner", {})
        if owner_data.get("id"):
            owner = self.db.query(User).filter(
                User.pb_id == owner_data["id"]
            ).first()
            if owner:
                note.owner_id = owner.id

        # Resolve customer
        customer_data = pb_note.get("customer", {})
        if customer_data.get("id"):
            customer = self.db.query(Customer).filter(
                Customer.pb_id == customer_data["id"]
            ).first()
            if customer:
                note.customer_id = customer.id

        # Store extra fields in custom_fields
        known_fields = {
            "id", "title", "content", "type", "source", "state",
            "createdAt", "updatedAt", "owner", "customer", "team"
        }
        custom = {k: v for k, v in pb_note.items() if k not in known_fields}
        if custom:
            note.custom_fields = custom
```

**Step 2: Add test to test_sync.py**

Append:

```python
from app.models import Note
from app.services.sync.notes_syncer import NotesSyncer


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
```

**Step 3: Run tests**

```bash
cd backend && pytest tests/test_sync.py -v
```

Expected: 2 tests pass

**Step 4: Commit**

```bash
git add backend/app/services/sync/ backend/tests/test_sync.py
git commit -m "feat: add Notes syncer with incremental sync support"
```

---

### Task 4.4: Create Sync Orchestrator

**Files:**
- Create: `backend/app/services/sync/orchestrator.py`
- Modify: `backend/app/services/sync/__init__.py`

**Step 1: Create orchestrator.py**

```python
import logging
from sqlalchemy.orm import Session

from app.services.sync.users_syncer import UsersSyncer
from app.services.sync.notes_syncer import NotesSyncer

logger = logging.getLogger(__name__)


class SyncOrchestrator:
    """Orchestrates the sync of all entities in correct order."""

    def __init__(self, db: Session):
        self.db = db

    async def run_full_sync(self) -> dict:
        """
        Run a full sync of all entities in dependency order.

        Order:
        1. Users & Teams (no dependencies)
        2. Companies (no dependencies)
        3. Customers (depends on companies)
        4. Components (no dependencies)
        5. Features (depends on components, users, teams)
        6. Notes (depends on customers, users, teams)
        7. Relationships (depends on notes, features)
        """
        results = {}

        # Phase 1: Independent entities
        logger.info("Syncing users...")
        users_syncer = UsersSyncer(self.db)
        results["users"] = await users_syncer.sync()

        # Phase 2: Notes (simplified for now - add more syncers later)
        logger.info("Syncing notes...")
        notes_syncer = NotesSyncer(self.db)
        results["notes"] = await notes_syncer.sync()

        logger.info(f"Sync complete: {results}")
        return results

    async def run_incremental_sync(self) -> dict:
        """Run incremental sync (same as full for now, but uses last_sync_time)."""
        return await self.run_full_sync()
```

**Step 2: Update sync/__init__.py**

```python
from app.services.sync.orchestrator import SyncOrchestrator
from app.services.sync.users_syncer import UsersSyncer
from app.services.sync.notes_syncer import NotesSyncer

__all__ = ["SyncOrchestrator", "UsersSyncer", "NotesSyncer"]
```

**Step 3: Commit**

```bash
git add backend/app/services/sync/
git commit -m "feat: add sync orchestrator for coordinated entity sync"
```

---

## Phase 5: API Endpoints

### Task 5.1: Create Health and Sync API Routes

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/sync.py`
- Modify: `backend/app/main.py`

**Step 1: Create api directory**

```bash
mkdir -p backend/app/api
```

**Step 2: Create api/__init__.py**

```python
# backend/app/api/__init__.py
```

**Step 3: Create sync.py**

```python
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.sync import SyncOrchestrator
from app.models import SyncHistory

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/trigger")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger an on-demand sync."""
    async def run_sync():
        orchestrator = SyncOrchestrator(db)
        await orchestrator.run_full_sync()

    background_tasks.add_task(run_sync)
    return {"message": "Sync triggered", "status": "running"}


@router.get("/status")
def get_sync_status(db: Session = Depends(get_db)):
    """Get current sync status."""
    running = (
        db.query(SyncHistory)
        .filter(SyncHistory.status == "running")
        .first()
    )

    if running:
        return {
            "status": "running",
            "entity_type": running.entity_type,
            "started_at": running.started_at,
        }

    return {"status": "idle"}


@router.get("/history")
def get_sync_history(
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Get past sync runs."""
    history = (
        db.query(SyncHistory)
        .order_by(SyncHistory.started_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": h.id,
            "entity_type": h.entity_type,
            "status": h.status,
            "started_at": h.started_at,
            "completed_at": h.completed_at,
            "records_synced": h.records_synced,
            "error_message": h.error_message,
        }
        for h in history
    ]
```

**Step 4: Update main.py to include router**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import sync

settings = get_settings()

app = FastAPI(
    title="ProductBoard Insights",
    description="Read-only reporting system for ProductBoard notes",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sync.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

**Step 5: Test endpoints**

```bash
cd backend && uvicorn app.main:app --reload &
sleep 2
curl http://localhost:8000/api/v1/sync/status
curl http://localhost:8000/api/v1/sync/history
```

Expected: JSON responses

**Step 6: Commit**

```bash
git add backend/app/api/ backend/app/main.py
git commit -m "feat: add sync API endpoints"
```

---

### Task 5.2: Create Notes API Routes

**Files:**
- Create: `backend/app/api/notes.py`
- Modify: `backend/app/main.py`

**Step 1: Create notes.py**

```python
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Note, User, Customer, NoteFeature, Feature

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("")
def list_notes(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    state: Optional[str] = None,
    owner_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    sort: str = "created_at",
    order: str = "desc",
    db: Session = Depends(get_db),
):
    """List notes with filtering and pagination."""
    query = db.query(Note)

    if state:
        query = query.filter(Note.state == state)
    if owner_id:
        query = query.filter(Note.owner_id == owner_id)
    if customer_id:
        query = query.filter(Note.customer_id == customer_id)

    # Sorting
    sort_col = getattr(Note, sort, Note.created_at)
    if order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    # Pagination
    total = query.count()
    notes = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "data": [_note_to_dict(n) for n in notes],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


@router.get("/stats")
def get_notes_stats(db: Session = Depends(get_db)):
    """Get aggregate note statistics."""
    total = db.query(Note).count()
    processed = db.query(Note).filter(Note.state == "processed").count()
    unprocessed = db.query(Note).filter(Note.state == "unprocessed").count()

    # Notes by type
    by_type = (
        db.query(Note.type, func.count(Note.id))
        .group_by(Note.type)
        .all()
    )

    # Notes by source
    by_source = (
        db.query(Note.source, func.count(Note.id))
        .group_by(Note.source)
        .all()
    )

    return {
        "total": total,
        "processed": processed,
        "unprocessed": unprocessed,
        "by_type": {t: c for t, c in by_type if t},
        "by_source": {s: c for s, c in by_source if s},
    }


@router.get("/{note_id}")
def get_note(note_id: int, db: Session = Depends(get_db)):
    """Get a single note with relationships."""
    note = db.query(Note).filter(Note.id == note_id).first()

    if not note:
        return {"error": "Note not found"}, 404

    # Get linked features
    feature_links = (
        db.query(Feature)
        .join(NoteFeature)
        .filter(NoteFeature.note_id == note_id)
        .all()
    )

    result = _note_to_dict(note)
    result["features"] = [
        {"id": f.id, "name": f.name, "product_area": f.product_area}
        for f in feature_links
    ]

    return result


def _note_to_dict(note: Note) -> dict:
    """Convert Note model to dict."""
    return {
        "id": note.id,
        "pb_id": note.pb_id,
        "title": note.title,
        "content": note.content,
        "type": note.type,
        "source": note.source,
        "state": note.state,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "processed_at": note.processed_at.isoformat() if note.processed_at else None,
        "owner_id": note.owner_id,
        "customer_id": note.customer_id,
    }
```

**Step 2: Update main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import sync, notes

settings = get_settings()

app = FastAPI(
    title="ProductBoard Insights",
    description="Read-only reporting system for ProductBoard notes",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sync.router, prefix="/api/v1")
app.include_router(notes.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

**Step 3: Commit**

```bash
git add backend/app/api/ backend/app/main.py
git commit -m "feat: add Notes API endpoints with stats"
```

---

### Task 5.3: Create Features API Routes

**Files:**
- Create: `backend/app/api/features.py`
- Modify: `backend/app/main.py`

**Step 1: Create features.py**

```python
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Feature, Note, NoteFeature, User

router = APIRouter(prefix="/features", tags=["features"])


@router.get("")
def list_features(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    product_area: Optional[str] = None,
    owner_id: Optional[int] = None,
    committed: Optional[bool] = None,
    sort: str = "created_at",
    order: str = "desc",
    db: Session = Depends(get_db),
):
    """List features with filtering and pagination."""
    query = db.query(Feature)

    if product_area:
        query = query.filter(Feature.product_area == product_area)
    if owner_id:
        query = query.filter(Feature.owner_id == owner_id)
    if committed is not None:
        query = query.filter(Feature.committed == committed)

    # Sorting
    sort_col = getattr(Feature, sort, Feature.created_at)
    if order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    total = query.count()
    features = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "data": [_feature_to_dict(f, db) for f in features],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


@router.get("/stats")
def get_features_stats(db: Session = Depends(get_db)):
    """Get aggregate feature statistics."""
    total = db.query(Feature).count()

    # By product area
    by_product_area = (
        db.query(Feature.product_area, func.count(Feature.id))
        .group_by(Feature.product_area)
        .all()
    )

    # By committed status
    committed = db.query(Feature).filter(Feature.committed == True).count()
    uncommitted = db.query(Feature).filter(Feature.committed == False).count()

    # By risk
    by_risk = (
        db.query(Feature.risk, func.count(Feature.id))
        .group_by(Feature.risk)
        .all()
    )

    return {
        "total": total,
        "committed": committed,
        "uncommitted": uncommitted,
        "by_product_area": {pa: c for pa, c in by_product_area if pa},
        "by_risk": {r: c for r, c in by_risk if r},
    }


@router.get("/{feature_id}")
def get_feature(feature_id: int, db: Session = Depends(get_db)):
    """Get a single feature with linked notes."""
    feature = db.query(Feature).filter(Feature.id == feature_id).first()

    if not feature:
        return {"error": "Feature not found"}, 404

    # Get linked notes
    note_links = (
        db.query(Note)
        .join(NoteFeature)
        .filter(NoteFeature.feature_id == feature_id)
        .all()
    )

    result = _feature_to_dict(feature, db)
    result["notes"] = [
        {
            "id": n.id,
            "title": n.title,
            "state": n.state,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in note_links
    ]
    result["note_count"] = len(note_links)

    return result


def _feature_to_dict(feature: Feature, db: Session) -> dict:
    """Convert Feature model to dict."""
    # Count linked notes
    note_count = (
        db.query(NoteFeature)
        .filter(NoteFeature.feature_id == feature.id)
        .count()
    )

    return {
        "id": feature.id,
        "pb_id": feature.pb_id,
        "name": feature.name,
        "description": feature.description,
        "type": feature.type,
        "status": feature.status,
        "product_area": feature.product_area,
        "product_area_stack_rank": feature.product_area_stack_rank,
        "committed": feature.committed,
        "risk": feature.risk,
        "owner_id": feature.owner_id,
        "created_at": feature.created_at.isoformat() if feature.created_at else None,
        "note_count": note_count,
    }
```

**Step 2: Update main.py**

Add import and router:

```python
from app.api import sync, notes, features

# In includes section:
app.include_router(features.router, prefix="/api/v1")
```

**Step 3: Commit**

```bash
git add backend/app/api/ backend/app/main.py
git commit -m "feat: add Features API endpoints with stats"
```

---

## Phase 6: Frontend Setup

### Task 6.1: Initialize React Frontend

**Files:**
- Create: `frontend/` (via create-react-app or vite)

**Step 1: Create frontend with Vite**

```bash
npm create vite@latest frontend -- --template react-ts
```

**Step 2: Install dependencies**

```bash
cd frontend && npm install
npm install @tanstack/react-query @tanstack/react-table recharts react-router-dom axios tailwindcss postcss autoprefixer
```

**Step 3: Initialize Tailwind**

```bash
cd frontend && npx tailwindcss init -p
```

**Step 4: Update tailwind.config.js**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

**Step 5: Update src/index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**Step 6: Test frontend starts**

```bash
cd frontend && npm run dev
```

Expected: Dev server on http://localhost:5173

**Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: initialize React frontend with Vite and Tailwind"
```

---

### Task 6.2: Create API Client

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/notes.ts`
- Create: `frontend/src/api/features.ts`

**Step 1: Create api directory**

```bash
mkdir -p frontend/src/api
```

**Step 2: Create client.ts**

```typescript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}
```

**Step 3: Create notes.ts**

```typescript
import { apiClient, PaginatedResponse } from './client';

export interface Note {
  id: number;
  pb_id: string;
  title: string;
  content: string;
  type: string;
  source: string;
  state: string;
  created_at: string | null;
  processed_at: string | null;
  owner_id: number | null;
  customer_id: number | null;
}

export interface NotesStats {
  total: number;
  processed: number;
  unprocessed: number;
  by_type: Record<string, number>;
  by_source: Record<string, number>;
}

export interface NotesParams {
  page?: number;
  limit?: number;
  state?: string;
  owner_id?: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

export const notesApi = {
  list: (params: NotesParams = {}) =>
    apiClient.get<PaginatedResponse<Note>>('/notes', { params }),

  get: (id: number) =>
    apiClient.get<Note & { features: Array<{ id: number; name: string }> }>(`/notes/${id}`),

  getStats: () =>
    apiClient.get<NotesStats>('/notes/stats'),
};
```

**Step 4: Create features.ts**

```typescript
import { apiClient, PaginatedResponse } from './client';

export interface Feature {
  id: number;
  pb_id: string;
  name: string;
  description: string;
  type: string;
  status: string;
  product_area: string;
  product_area_stack_rank: number | null;
  committed: boolean;
  risk: string;
  owner_id: number | null;
  created_at: string | null;
  note_count: number;
}

export interface FeaturesStats {
  total: number;
  committed: number;
  uncommitted: number;
  by_product_area: Record<string, number>;
  by_risk: Record<string, number>;
}

export interface FeaturesParams {
  page?: number;
  limit?: number;
  product_area?: string;
  owner_id?: number;
  committed?: boolean;
  sort?: string;
  order?: 'asc' | 'desc';
}

export const featuresApi = {
  list: (params: FeaturesParams = {}) =>
    apiClient.get<PaginatedResponse<Feature>>('/features', { params }),

  get: (id: number) =>
    apiClient.get<Feature & { notes: Array<{ id: number; title: string }> }>(`/features/${id}`),

  getStats: () =>
    apiClient.get<FeaturesStats>('/features/stats'),
};
```

**Step 5: Commit**

```bash
git add frontend/src/api/
git commit -m "feat: add API client for notes and features"
```

---

### Task 6.3: Create Dashboard Page

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/components/StatCard.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Create components directory**

```bash
mkdir -p frontend/src/pages frontend/src/components
```

**Step 2: Create StatCard.tsx**

```typescript
interface StatCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  onClick?: () => void;
}

export function StatCard({ title, value, subtitle, onClick }: StatCardProps) {
  return (
    <div
      className={`bg-white rounded-lg shadow p-6 ${onClick ? 'cursor-pointer hover:shadow-lg transition-shadow' : ''}`}
      onClick={onClick}
    >
      <h3 className="text-sm font-medium text-gray-500">{title}</h3>
      <p className="mt-2 text-3xl font-semibold text-gray-900">{value}</p>
      {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
    </div>
  );
}
```

**Step 3: Create Dashboard.tsx**

```typescript
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { notesApi } from '../api/notes';
import { featuresApi } from '../api/features';
import { StatCard } from '../components/StatCard';

export function Dashboard() {
  const navigate = useNavigate();

  const { data: notesStats, isLoading: notesLoading } = useQuery({
    queryKey: ['notes', 'stats'],
    queryFn: () => notesApi.getStats().then(r => r.data),
  });

  const { data: featuresStats, isLoading: featuresLoading } = useQuery({
    queryKey: ['features', 'stats'],
    queryFn: () => featuresApi.getStats().then(r => r.data),
  });

  if (notesLoading || featuresLoading) {
    return <div className="p-8">Loading...</div>;
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Total Notes"
          value={notesStats?.total || 0}
          onClick={() => navigate('/notes')}
        />
        <StatCard
          title="Processed"
          value={notesStats?.processed || 0}
          subtitle={`${Math.round((notesStats?.processed || 0) / (notesStats?.total || 1) * 100)}%`}
          onClick={() => navigate('/notes?state=processed')}
        />
        <StatCard
          title="Unprocessed"
          value={notesStats?.unprocessed || 0}
          onClick={() => navigate('/notes?state=unprocessed')}
        />
        <StatCard
          title="Total Features"
          value={featuresStats?.total || 0}
          onClick={() => navigate('/features')}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Notes by Type</h2>
          <div className="space-y-2">
            {Object.entries(notesStats?.by_type || {}).map(([type, count]) => (
              <div key={type} className="flex justify-between">
                <span className="text-gray-600">{type}</span>
                <span className="font-medium">{count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Features by Product Area</h2>
          <div className="space-y-2">
            {Object.entries(featuresStats?.by_product_area || {}).map(([area, count]) => (
              <div key={area} className="flex justify-between">
                <span className="text-gray-600">{area}</span>
                <span className="font-medium">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
```

**Step 4: Update App.tsx**

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-100">
          <nav className="bg-white shadow">
            <div className="max-w-7xl mx-auto px-4 py-4">
              <h1 className="text-xl font-bold text-gray-900">
                ProductBoard Insights
              </h1>
            </div>
          </nav>
          <main className="max-w-7xl mx-auto">
            <Routes>
              <Route path="/" element={<Dashboard />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
```

**Step 5: Test frontend**

```bash
cd frontend && npm run dev
```

Expected: Dashboard page loads (may show empty data if no backend running)

**Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: add Dashboard page with stats cards"
```

---

## Summary: Remaining Tasks

This plan covers Phases 1-6 which establish the foundation:
- Backend project structure
- Database models and migrations
- ProductBoard API client
- Sync engine (basic)
- Core API endpoints
- Frontend setup with dashboard

**Remaining phases to implement:**
- Phase 7: Notes list/detail pages with drill-down
- Phase 8: Features list/detail pages
- Phase 9: Management reports (PM workload, SLA tracking)
- Phase 10: Export service (PDF/JSON generation)
- Phase 11: Scheduler (APScheduler for periodic sync/exports)
- Phase 12: Authentication (basic auth)
- Phase 13: Docker setup refinement

Each phase follows the same TDD pattern: write test, verify fail, implement, verify pass, commit.
