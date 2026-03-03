# MCP Server Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an MCP server mounted at `/mcp` in the existing FastAPI app, exposing 14 tools for querying notes, running analytics, and triggering syncs — accessible from Claude.ai over HTTPS with bearer token auth.

**Architecture:** The MCP server is a Starlette ASGI sub-app created with `FastMCP`, wrapped in a bearer token middleware, and mounted into the existing FastAPI app at `/mcp`. It imports SQLAlchemy models directly from `app.models` for direct DB access — no HTTP hop.

**Tech Stack:** Python, `mcp[cli]>=1.0.0` (FastMCP), SQLAlchemy 2.x, Starlette middleware, SQLite via existing `app.database.SessionLocal`

---

## Context: Key Files

- `backend/app/main.py` — where we mount the MCP sub-app
- `backend/app/config.py` — where we add `MCP_API_KEY` setting
- `backend/app/database.py` — exports `SessionLocal` and `get_db`
- `backend/app/models/__init__.py` — exports `Note`, `Member`, `Company`, `Feature`, `NoteFeature`, `NoteComment`, `SyncHistory`
- `backend/requirements.txt` — add `mcp[cli]>=1.0.0`

**Important:** The existing catch-all frontend route `@app.get("/{full_path:path}")` in `main.py` must stay AFTER the `/mcp` mount, or it will intercept MCP traffic. Mount `/mcp` before the `if FRONTEND_DIR.exists():` block.

---

## Task 1: Add dependency and MCP_API_KEY config

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`

**Step 1: Add mcp to requirements**

Add to `backend/requirements.txt`:
```
mcp[cli]>=1.0.0
```

**Step 2: Add MCP_API_KEY to Settings**

In `backend/app/config.py`, add one field inside `class Settings`:
```python
# MCP Server
mcp_api_key: str = ""
```
Place it after the `# Auth` block. The full class should look like:
```python
class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./pdb_insights.db"

    # ProductBoard API
    productboard_api_token: str = ""
    productboard_api_url: str = "https://api.productboard.com"

    # Auth
    auth_username: str = "admin"
    auth_password: str = "changeme"
    session_secret: str = "change-this-secret-key"
    secure_cookies: bool = False

    # MCP Server
    mcp_api_key: str = ""

    # Sync
    sync_interval_hours: int = 4
    sync_enabled: bool = True

    # Exports
    export_schedule_hour: int = 2
    export_retention_days: int = 30
    export_path: str = "./exports"

    class Config:
        env_file = ".env"
```

**Step 3: Install the dependency**

Run from `backend/`:
```bash
pip install mcp[cli]
```
Expected: installs without error.

**Step 4: Verify import works**

```bash
python3 -c "from mcp.server.fastmcp import FastMCP; print('ok')"
```
Expected: prints `ok`

**Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/config.py
git commit -m "feat(mcp): add mcp dependency and MCP_API_KEY config"
```

---

## Task 2: Create bearer token auth middleware

**Files:**
- Create: `backend/mcp/__init__.py`
- Create: `backend/mcp/auth.py`
- Create: `backend/mcp/tools/__init__.py`

**Step 1: Write the failing test**

Create `backend/tests/test_mcp_auth.py`:
```python
import pytest
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.middleware import Middleware

from mcp.auth import BearerAuthMiddleware


def homepage(request):
    return PlainTextResponse("ok")


def make_app(api_key: str):
    return Starlette(
        routes=[Route("/", homepage)],
        middleware=[Middleware(BearerAuthMiddleware, api_key=api_key)],
    )


def test_missing_auth_header_returns_401():
    app = make_app("secret")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/")
    assert response.status_code == 401


def test_wrong_token_returns_401():
    app = make_app("secret")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/", headers={"Authorization": "Bearer wrongtoken"})
    assert response.status_code == 401


def test_correct_token_passes_through():
    app = make_app("secret")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/", headers={"Authorization": "Bearer secret"})
    assert response.status_code == 200
    assert response.text == "ok"


def test_non_bearer_scheme_returns_401():
    app = make_app("secret")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/", headers={"Authorization": "Basic secret"})
    assert response.status_code == 401
```

**Step 2: Run test to verify it fails**

```bash
cd backend && python3 -m pytest tests/test_mcp_auth.py -v
```
Expected: `ImportError: No module named 'mcp.auth'` or similar.

**Step 3: Create the mcp package**

Create `backend/mcp/__init__.py` (empty):
```python
```

Create `backend/mcp/tools/__init__.py` (empty):
```python
```

**Step 4: Implement the middleware**

Create `backend/mcp/auth.py`:
```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class BearerAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key: str):
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        token = auth_header[len("Bearer "):]
        if token != self.api_key:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)
```

**Step 5: Run test to verify it passes**

```bash
cd backend && python3 -m pytest tests/test_mcp_auth.py -v
```
Expected: 4 tests pass.

**Step 6: Commit**

```bash
git add backend/mcp/ backend/tests/test_mcp_auth.py
git commit -m "feat(mcp): add bearer token auth middleware"
```

---

## Task 3: Implement note query tools

**Files:**
- Create: `backend/mcp/tools/notes.py`
- Create: `backend/tests/test_mcp_notes.py`

These are the tools: `list_notes`, `get_note`, `search_notes`, `get_notes_stats`, `list_members`, `list_companies`, `list_features`.

The tools use a `_get_db()` helper that returns a `SessionLocal()`. Tests pass a real in-memory SQLite session directly to the `_impl` functions.

**Step 1: Write the failing tests**

Create `backend/tests/test_mcp_notes.py`:
```python
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
```

**Step 2: Run tests to verify they fail**

```bash
cd backend && python3 -m pytest tests/test_mcp_notes.py -v
```
Expected: `ImportError` - module not found.

**Step 3: Implement notes tools**

Create `backend/mcp/tools/notes.py`:
```python
import json
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.models import Note, Member, Company, Feature, NoteFeature, NoteComment
from app.database import SessionLocal


# ── helpers ──────────────────────────────────────────────────────────────────

def _member_dict(member: Optional[Member]) -> Optional[dict]:
    if not member:
        return None
    return {"id": member.id, "name": member.name, "email": member.email}


def _note_dict(note: Note, db: Session) -> dict:
    owner = db.get(Member, note.owner_id) if note.owner_id else None
    creator = db.get(Member, note.created_by_id) if note.created_by_id else None
    company = db.get(Company, note.company_id) if note.company_id else None
    response_time = None
    if note.processed_at and note.created_at:
        response_time = round((note.processed_at - note.created_at).total_seconds() / 86400, 1)
    return {
        "id": note.id,
        "pb_id": note.pb_id,
        "title": note.title,
        "content": note.content,
        "state": note.state,
        "source_origin": note.source_origin,
        "display_url": note.display_url,
        "tags": note.tags or [],
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        "processed_at": note.processed_at.isoformat() if note.processed_at else None,
        "response_time_days": response_time,
        "owner": _member_dict(owner),
        "creator": _member_dict(creator),
        "company": {"id": company.id, "name": company.name} if company else None,
    }


# ── impl functions (testable, accept db session) ──────────────────────────────

def _list_notes_impl(
    db: Session,
    state: Optional[str] = None,
    owner_id: Optional[int] = None,
    creator_id: Optional[int] = None,
    company_id: Optional[int] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    sort: str = "created_at",
    order: str = "desc",
    group_by: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
) -> dict:
    query = db.query(Note).filter(Note.deleted_at.is_(None))
    if state:
        query = query.filter(Note.state == state)
    if owner_id:
        query = query.filter(Note.owner_id == owner_id)
    if creator_id:
        query = query.filter(Note.created_by_id == creator_id)
    if company_id:
        query = query.filter(Note.company_id == company_id)
    if created_after:
        query = query.filter(Note.created_at >= created_after)
    if created_before:
        dt = datetime.strptime(created_before, "%Y-%m-%d") + timedelta(days=1)
        query = query.filter(Note.created_at < dt)

    sort_col = getattr(Note, sort, Note.created_at)
    query = query.order_by(sort_col.desc() if order == "desc" else sort_col.asc())

    # Group counts
    group_counts = None
    if group_by in ("owner", "creator", "company"):
        if group_by == "owner":
            rows = (
                db.query(
                    func.coalesce(Member.name, Member.email, "Unassigned").label("g"),
                    func.count(Note.id),
                )
                .select_from(Note)
                .outerjoin(Member, Note.owner_id == Member.id)
                .filter(Note.deleted_at.is_(None))
                .group_by("g")
                .all()
            )
        elif group_by == "creator":
            rows = (
                db.query(
                    func.coalesce(Member.name, Member.email, "Unknown").label("g"),
                    func.count(Note.id),
                )
                .select_from(Note)
                .outerjoin(Member, Note.created_by_id == Member.id)
                .filter(Note.deleted_at.is_(None))
                .group_by("g")
                .all()
            )
        else:  # company
            rows = (
                db.query(
                    func.coalesce(Company.name, "No Company").label("g"),
                    func.count(Note.id),
                )
                .select_from(Note)
                .outerjoin(Company, Note.company_id == Company.id)
                .filter(Note.deleted_at.is_(None))
                .group_by("g")
                .all()
            )
        group_counts = {name: count for name, count in rows}

    total = query.count()
    notes = query.offset((page - 1) * limit).limit(limit).all()
    return {
        "data": [_note_dict(n, db) for n in notes],
        "group_counts": group_counts,
        "pagination": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit},
    }


def _get_note_impl(db: Session, note_id: int) -> Optional[dict]:
    note = db.query(Note).filter(Note.id == note_id, Note.deleted_at.is_(None)).first()
    if not note:
        return None
    result = _note_dict(note, db)
    result["features"] = [
        {"id": f.id, "pb_id": f.pb_id, "name": f.name, "display_url": f.display_url, "importance": importance}
        for f, importance in (
            db.query(Feature, NoteFeature.importance)
            .join(NoteFeature)
            .filter(NoteFeature.note_id == note_id)
            .all()
        )
    ]
    result["comments"] = [
        {
            "id": c.id,
            "content": c.content,
            "timestamp": c.timestamp.isoformat() if c.timestamp else None,
            "member": _member_dict(db.get(Member, c.member_id)) if c.member_id else None,
        }
        for c in (
            db.query(NoteComment)
            .filter(NoteComment.note_id == note_id)
            .order_by(NoteComment.timestamp.desc())
            .limit(10)
            .all()
        )
    ]
    return result


def _search_notes_impl(db: Session, query: str, state: Optional[str] = None, page: int = 1, limit: int = 50) -> dict:
    q = (
        db.query(Note)
        .filter(Note.deleted_at.is_(None))
        .filter(or_(Note.title.ilike(f"%{query}%"), Note.content.ilike(f"%{query}%")))
    )
    if state:
        q = q.filter(Note.state == state)
    q = q.order_by(Note.created_at.desc())
    total = q.count()
    notes = q.offset((page - 1) * limit).limit(limit).all()
    return {
        "data": [_note_dict(n, db) for n in notes],
        "pagination": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit},
    }


def _get_notes_stats_impl(db: Session) -> dict:
    base = db.query(Note).filter(Note.deleted_at.is_(None))
    total = base.count()
    processed = base.filter(Note.state == "processed").count()
    unprocessed = base.filter(Note.state == "unprocessed").count()
    processed_notes = base.filter(Note.state == "processed", Note.processed_at.isnot(None)).all()
    rts = [
        round((n.processed_at - n.created_at).total_seconds() / 86400, 1)
        for n in processed_notes
        if n.processed_at and n.created_at
    ]
    avg_rt = round(sum(rts) / len(rts), 1) if rts else None
    return {"total": total, "processed": processed, "unprocessed": unprocessed, "avg_response_time_days": avg_rt}


def _list_members_impl(db: Session) -> list:
    members = db.query(Member).order_by(Member.name).all()
    return [{"id": m.id, "name": m.name or m.email, "email": m.email} for m in members]


def _list_companies_impl(db: Session) -> list:
    companies = db.query(Company).order_by(Company.name).all()
    return [{"id": c.id, "name": c.name, "domain": c.domain} for c in companies]


def _list_features_impl(db: Session) -> list:
    rows = (
        db.query(Feature, func.count(NoteFeature.note_id).label("note_count"))
        .outerjoin(NoteFeature, Feature.id == NoteFeature.feature_id)
        .group_by(Feature.id)
        .order_by(Feature.name)
        .all()
    )
    return [
        {"id": f.id, "pb_id": f.pb_id, "name": f.name, "display_url": f.display_url, "note_count": count}
        for f, count in rows
    ]


# ── MCP tool wrappers (registered in server.py) ───────────────────────────────

def register_note_tools(mcp):
    """Register all note tools on the FastMCP instance."""

    @mcp.tool()
    def list_notes(
        state: Optional[str] = None,
        owner_id: Optional[int] = None,
        creator_id: Optional[int] = None,
        company_id: Optional[int] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        sort: str = "created_at",
        order: str = "desc",
        group_by: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> str:
        """List notes with optional filters (state, owner_id, company_id, date range) and grouping (owner/creator/company)."""
        db = SessionLocal()
        try:
            return json.dumps(_list_notes_impl(db, state, owner_id, creator_id, company_id, created_after, created_before, sort, order, group_by, page, limit))
        finally:
            db.close()

    @mcp.tool()
    def get_note(note_id: int) -> str:
        """Get full details for a single note including features and comments."""
        db = SessionLocal()
        try:
            result = _get_note_impl(db, note_id)
            if result is None:
                return json.dumps({"error": f"Note {note_id} not found"})
            return json.dumps(result)
        finally:
            db.close()

    @mcp.tool()
    def search_notes(query: str, state: Optional[str] = None, page: int = 1, limit: int = 50) -> str:
        """Full-text search notes by title and content."""
        db = SessionLocal()
        try:
            return json.dumps(_search_notes_impl(db, query, state, page, limit))
        finally:
            db.close()

    @mcp.tool()
    def get_notes_stats() -> str:
        """Get all-time aggregate stats: total, processed, unprocessed, avg response time."""
        db = SessionLocal()
        try:
            return json.dumps(_get_notes_stats_impl(db))
        finally:
            db.close()

    @mcp.tool()
    def list_members() -> str:
        """List all ProductBoard members/PMs with their IDs."""
        db = SessionLocal()
        try:
            return json.dumps(_list_members_impl(db))
        finally:
            db.close()

    @mcp.tool()
    def list_companies() -> str:
        """List all companies with their IDs."""
        db = SessionLocal()
        try:
            return json.dumps(_list_companies_impl(db))
        finally:
            db.close()

    @mcp.tool()
    def list_features() -> str:
        """List all features with linked note counts."""
        db = SessionLocal()
        try:
            return json.dumps(_list_features_impl(db))
        finally:
            db.close()
```

**Step 4: Run tests to verify they pass**

```bash
cd backend && python3 -m pytest tests/test_mcp_notes.py -v
```
Expected: all 12 tests pass.

**Step 5: Commit**

```bash
git add backend/mcp/tools/notes.py backend/tests/test_mcp_notes.py
git commit -m "feat(mcp): add note query tools with tests"
```

---

## Task 4: Implement analytics (reports) tools

**Files:**
- Create: `backend/mcp/tools/reports.py`
- Create: `backend/tests/test_mcp_reports.py`

Tools: `get_notes_insights`, `get_notes_trend`, `get_response_time_stats`, `get_sla_report`, `get_pm_workload`.

**Step 1: Write the failing tests**

Create `backend/tests/test_mcp_reports.py`:
```python
import json
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
```

**Step 2: Run tests to verify they fail**

```bash
cd backend && python3 -m pytest tests/test_mcp_reports.py -v
```
Expected: `ImportError` - module not found.

**Step 3: Implement reports tools**

Create `backend/mcp/tools/reports.py`:
```python
import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Note, Member, Company
from app.database import SessionLocal

SLA_DAYS = 5


def _calc_rt(note: Note) -> Optional[float]:
    if note.processed_at and note.created_at:
        return round((note.processed_at - note.created_at).total_seconds() / 86400, 1)
    return None


def _get_notes_insights_impl(db: Session, days: int = 90) -> dict:
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)
    prev_start = period_start - timedelta(days=days)
    base = db.query(Note).filter(Note.deleted_at.is_(None))

    def count(q): return q.scalar() or 0

    cur_total = count(base.with_entities(func.count(Note.id)).filter(Note.created_at >= period_start))
    cur_processed = count(base.with_entities(func.count(Note.id)).filter(Note.created_at >= period_start, Note.state == "processed"))
    cur_unprocessed = count(base.with_entities(func.count(Note.id)).filter(Note.created_at >= period_start, Note.state == "unprocessed"))
    cur_unassigned = count(base.with_entities(func.count(Note.id)).filter(Note.created_at >= period_start, Note.owner_id.is_(None)))

    prev_total = count(base.with_entities(func.count(Note.id)).filter(Note.created_at >= prev_start, Note.created_at < period_start))
    prev_processed = count(base.with_entities(func.count(Note.id)).filter(Note.created_at >= prev_start, Note.created_at < period_start, Note.state == "processed"))
    prev_unprocessed = count(base.with_entities(func.count(Note.id)).filter(Note.created_at >= prev_start, Note.created_at < period_start, Note.state == "unprocessed"))
    prev_unassigned = count(base.with_entities(func.count(Note.id)).filter(Note.created_at >= prev_start, Note.created_at < period_start, Note.owner_id.is_(None)))

    def pct_change(cur, prev):
        if prev == 0:
            return None if cur == 0 else 100.0
        return round(((cur - prev) / prev) * 100, 1)

    # Avg response time
    proc_notes = db.query(Note).filter(Note.deleted_at.is_(None), Note.created_at >= period_start, Note.state == "processed", Note.processed_at.isnot(None)).all()
    rts = [_calc_rt(n) for n in proc_notes if _calc_rt(n) is not None]
    avg_rt = round(sum(rts) / len(rts), 1) if rts else None

    prev_proc = db.query(Note).filter(Note.deleted_at.is_(None), Note.created_at >= prev_start, Note.created_at < period_start, Note.state == "processed", Note.processed_at.isnot(None)).all()
    prev_rts = [_calc_rt(n) for n in prev_proc if _calc_rt(n) is not None]
    prev_avg_rt = round(sum(prev_rts) / len(prev_rts), 1) if prev_rts else None

    # By owner
    sla_threshold = now - timedelta(days=SLA_DAYS)
    owners_rows = (
        db.query(Member.id, Member.name, Member.email,
                 func.count(Note.id).label("assigned"))
        .join(Note, Note.owner_id == Member.id)
        .filter(Note.deleted_at.is_(None), Note.created_at >= period_start)
        .group_by(Member.id, Member.name, Member.email)
        .all()
    )
    sla_breached = dict(
        db.query(Note.owner_id, func.count(Note.id))
        .filter(Note.deleted_at.is_(None), Note.state == "unprocessed", Note.created_at >= period_start, Note.created_at < sla_threshold)
        .group_by(Note.owner_id).all()
    )
    owner_rts = defaultdict(list)
    for n in proc_notes:
        if n.owner_id:
            rt = _calc_rt(n)
            if rt is not None:
                owner_rts[n.owner_id].append(rt)

    processed_by_owner = dict(
        db.query(Note.owner_id, func.count(Note.id))
        .filter(Note.deleted_at.is_(None), Note.created_at >= period_start, Note.state == "processed")
        .group_by(Note.owner_id).all()
    )
    unprocessed_by_owner = dict(
        db.query(Note.owner_id, func.count(Note.id))
        .filter(Note.deleted_at.is_(None), Note.created_at >= period_start, Note.state == "unprocessed")
        .group_by(Note.owner_id).all()
    )

    by_owner = []
    for mid, name, email, assigned in owners_rows:
        processed = processed_by_owner.get(mid, 0)
        unprocessed = unprocessed_by_owner.get(mid, 0)
        orts = owner_rts.get(mid, [])
        by_owner.append({
            "id": mid, "name": name or email or "Unknown",
            "assigned": assigned, "processed": processed, "unprocessed": unprocessed,
            "progress": round(processed / assigned * 100) if assigned else 0,
            "avg_response_time": round(sum(orts) / len(orts), 1) if orts else None,
            "sla_breached": sla_breached.get(mid, 0),
        })
    by_owner.sort(key=lambda x: x["assigned"], reverse=True)

    return {
        "period_days": days,
        "summary": {
            "created": {"value": cur_total, "change": pct_change(cur_total, prev_total)},
            "processed": {"value": cur_processed, "change": pct_change(cur_processed, prev_processed)},
            "unprocessed": {"value": cur_unprocessed, "change": pct_change(cur_unprocessed, prev_unprocessed)},
            "unassigned": {"value": cur_unassigned, "change": pct_change(cur_unassigned, prev_unassigned)},
            "avg_response_time": {"value": avg_rt, "change": None if (avg_rt is None or prev_avg_rt is None or prev_avg_rt == 0) else round(((avg_rt - prev_avg_rt) / prev_avg_rt) * 100, 1)},
        },
        "by_owner": by_owner,
    }


def _get_notes_trend_impl(db: Session, days: int = 90) -> dict:
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)
    notes = db.query(Note).filter(Note.deleted_at.is_(None), Note.created_at >= period_start).all()
    weekly_created = defaultdict(int)
    weekly_processed = defaultdict(int)
    for note in notes:
        if note.created_at:
            w = note.created_at.isocalendar()
            key = f"{w[0]}-W{w[1]:02d}"
            weekly_created[key] += 1
            if note.state == "processed":
                weekly_processed[key] += 1
    all_weeks = sorted(set(weekly_created) | set(weekly_processed))
    return {"data": [{"week": w, "created": weekly_created.get(w, 0), "processed": weekly_processed.get(w, 0)} for w in all_weeks]}


def _get_response_time_stats_impl(db: Session, days: int = 90) -> dict:
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)
    notes = db.query(Note).filter(Note.deleted_at.is_(None), Note.created_at >= period_start, Note.state == "processed", Note.processed_at.isnot(None)).all()
    rts = [(n, _calc_rt(n)) for n in notes if _calc_rt(n) is not None]
    if not rts:
        return {"average_days": None, "median_days": None, "distribution": [], "by_owner": []}
    vals = sorted(r for _, r in rts)
    avg = round(sum(vals) / len(vals), 1)
    median = vals[len(vals) // 2]
    buckets = {"<1 day": 0, "1-3 days": 0, "3-5 days": 0, "5+ days": 0}
    for v in vals:
        if v < 1: buckets["<1 day"] += 1
        elif v < 3: buckets["1-3 days"] += 1
        elif v < 5: buckets["3-5 days"] += 1
        else: buckets["5+ days"] += 1
    owner_data = defaultdict(list)
    for note, rt in rts:
        if note.owner_id:
            owner_data[note.owner_id].append(rt)
    by_owner = []
    for oid, orts in owner_data.items():
        m = db.get(Member, oid)
        if m:
            by_owner.append({"id": oid, "name": m.name or m.email, "avg_response_time": round(sum(orts) / len(orts), 1), "count": len(orts)})
    by_owner.sort(key=lambda x: x["avg_response_time"])
    return {"average_days": avg, "median_days": median, "distribution": [{"bucket": k, "count": v} for k, v in buckets.items()], "by_owner": by_owner}


def _get_sla_report_impl(db: Session, days: Optional[int] = None) -> dict:
    now = datetime.utcnow()
    sla_threshold = now - timedelta(days=SLA_DAYS)
    warning_threshold = now - timedelta(days=SLA_DAYS - 1)
    q = db.query(Note).filter(Note.deleted_at.is_(None), Note.state == "unprocessed")
    if days:
        q = q.filter(Note.created_at >= now - timedelta(days=days))
    notes = q.all()
    breached, at_risk, on_track = [], [], []
    owner_ids = {n.owner_id for n in notes if n.owner_id}
    owners_map = {m.id: m.name or m.email for m in db.query(Member).filter(Member.id.in_(owner_ids)).all()} if owner_ids else {}
    company_ids = {n.company_id for n in notes if n.company_id}
    companies_map = {c.id: c.name for c in db.query(Company).filter(Company.id.in_(company_ids)).all()} if company_ids else {}
    for note in notes:
        if not note.created_at:
            continue
        d = {
            "id": note.id, "title": note.title,
            "created_at": note.created_at.isoformat(),
            "days_old": (now - note.created_at).days,
            "owner_id": note.owner_id,
            "owner_name": owners_map.get(note.owner_id) if note.owner_id else None,
            "company_name": companies_map.get(note.company_id) if note.company_id else None,
        }
        if note.created_at < sla_threshold:
            breached.append(d)
        elif note.created_at < warning_threshold:
            at_risk.append(d)
        else:
            on_track.append(d)
    breached.sort(key=lambda x: x["days_old"], reverse=True)
    at_risk.sort(key=lambda x: x["days_old"], reverse=True)
    return {
        "summary": {
            "total_unprocessed": len(notes),
            "breached": len(breached), "at_risk": len(at_risk), "on_track": len(on_track),
            "sla_compliance_rate": round((1 - len(breached) / max(len(notes), 1)) * 100, 1),
        },
        "breached_notes": breached[:50], "at_risk_notes": at_risk[:50],
        "sla_days": SLA_DAYS,
    }


def _get_pm_workload_impl(db: Session) -> dict:
    rows = (
        db.query(Member.id, Member.name, Member.email,
                 func.count(Note.id).label("total"),
                 func.sum(func.cast(Note.state == "unprocessed", func.Integer if hasattr(func, 'Integer') else type(1))).label("unprocessed"))
        .outerjoin(Note, Note.owner_id == Member.id)
        .filter(Note.deleted_at.is_(None) if Note.deleted_at is not None else True)
        .group_by(Member.id, Member.name, Member.email)
        .all()
    )
    # Simpler query for workload
    all_members = db.query(Member).all()
    workload = []
    for m in all_members:
        total = db.query(Note).filter(Note.owner_id == m.id, Note.deleted_at.is_(None)).count()
        unproc = db.query(Note).filter(Note.owner_id == m.id, Note.deleted_at.is_(None), Note.state == "unprocessed").count()
        proc = db.query(Note).filter(Note.owner_id == m.id, Note.deleted_at.is_(None), Note.state == "processed").count()
        workload.append({"id": m.id, "name": m.name or m.email, "email": m.email, "total_notes": total, "unprocessed_notes": unproc, "processed_notes": proc})
    workload.sort(key=lambda x: x["unprocessed_notes"], reverse=True)
    return {
        "data": workload,
        "summary": {
            "total_users": len(workload),
            "total_unprocessed": sum(w["unprocessed_notes"] for w in workload),
            "total_processed": sum(w["processed_notes"] for w in workload),
        },
    }


def register_report_tools(mcp):
    """Register all analytics tools on the FastMCP instance."""

    @mcp.tool()
    def get_notes_insights(days: int = 90) -> str:
        """Get the full Insights dashboard: summary metrics with period-over-period changes and owner performance table."""
        db = SessionLocal()
        try:
            return json.dumps(_get_notes_insights_impl(db, days))
        finally:
            db.close()

    @mcp.tool()
    def get_notes_trend(days: int = 90) -> str:
        """Get weekly notes trend: created vs processed per week for the given period."""
        db = SessionLocal()
        try:
            return json.dumps(_get_notes_trend_impl(db, days))
        finally:
            db.close()

    @mcp.tool()
    def get_response_time_stats(days: int = 90) -> str:
        """Get response time analytics: average, median, distribution buckets, and per-PM breakdown."""
        db = SessionLocal()
        try:
            return json.dumps(_get_response_time_stats_impl(db, days))
        finally:
            db.close()

    @mcp.tool()
    def get_sla_report(days: Optional[int] = None) -> str:
        """Get SLA compliance report: breached (>5 days unprocessed), at-risk, and on-track notes with owner breakdown."""
        db = SessionLocal()
        try:
            return json.dumps(_get_sla_report_impl(db, days))
        finally:
            db.close()

    @mcp.tool()
    def get_pm_workload() -> str:
        """Get workload per PM: total, processed, and unprocessed note counts."""
        db = SessionLocal()
        try:
            return json.dumps(_get_pm_workload_impl(db))
        finally:
            db.close()
```

**Step 4: Run tests to verify they pass**

```bash
cd backend && python3 -m pytest tests/test_mcp_reports.py -v
```
Expected: all 6 tests pass.

**Step 5: Commit**

```bash
git add backend/mcp/tools/reports.py backend/tests/test_mcp_reports.py
git commit -m "feat(mcp): add analytics report tools with tests"
```

---

## Task 5: Implement sync action tools

**Files:**
- Create: `backend/mcp/tools/sync.py`
- Create: `backend/tests/test_mcp_sync.py`

Tools: `trigger_sync`, `get_sync_status`, `get_sync_history`.

**Step 1: Write the failing tests**

Create `backend/tests/test_mcp_sync.py`:
```python
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import SyncHistory
from mcp.tools.sync import _get_sync_status_impl, _get_sync_history_impl


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
```

**Step 2: Run tests to verify they fail**

```bash
cd backend && python3 -m pytest tests/test_mcp_sync.py -v
```
Expected: `ImportError`.

**Step 3: Implement sync tools**

Create `backend/mcp/tools/sync.py`:
```python
import asyncio
import json
import logging
from datetime import timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import SyncHistory
from app.database import SessionLocal, SessionLocal as SL

logger = logging.getLogger(__name__)


def _fmt_dt(dt) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _get_sync_status_impl(db: Session) -> dict:
    running = db.query(SyncHistory).filter(SyncHistory.status == "running").first()
    last = (
        db.query(SyncHistory)
        .filter(SyncHistory.status.in_(["completed", "partial"]))
        .order_by(desc(SyncHistory.completed_at))
        .first()
    )
    if running:
        return {
            "status": "running",
            "entity_type": running.entity_type,
            "started_at": _fmt_dt(running.started_at),
            "last_sync_at": _fmt_dt(last.completed_at) if last else None,
        }
    return {
        "status": "idle",
        "last_sync_at": _fmt_dt(last.completed_at) if last else None,
        "last_records_synced": last.records_synced if last else None,
    }


def _get_sync_history_impl(db: Session, limit: int = 10) -> list:
    rows = (
        db.query(SyncHistory)
        .order_by(desc(SyncHistory.started_at))
        .limit(limit)
        .all()
    )
    return [
        {
            "id": h.id,
            "entity_type": h.entity_type,
            "status": h.status,
            "started_at": _fmt_dt(h.started_at),
            "completed_at": _fmt_dt(h.completed_at),
            "records_synced": h.records_synced,
            "error_message": h.error_message,
        }
        for h in rows
    ]


def register_sync_tools(mcp):
    """Register all sync tools on the FastMCP instance."""

    @mcp.tool()
    def trigger_sync() -> str:
        """Trigger an immediate ProductBoard data sync. Returns error if sync already running."""
        from app.services.sync import SyncOrchestrator

        db = SessionLocal()
        try:
            running = db.query(SyncHistory).filter(SyncHistory.status == "running").first()
            if running:
                return json.dumps({"triggered": False, "message": "Sync already in progress"})
        finally:
            db.close()

        async def _run():
            sdb = SL()
            try:
                orchestrator = SyncOrchestrator(sdb)
                await orchestrator.run_full_sync()
            except Exception as e:
                logger.exception(f"MCP-triggered sync failed: {e}")
            finally:
                sdb.close()

        try:
            loop = asyncio.get_event_loop()
            loop.create_task(_run())
        except RuntimeError:
            asyncio.run(_run())

        return json.dumps({"triggered": True, "message": "Sync started"})

    @mcp.tool()
    def get_sync_status() -> str:
        """Check if a sync is currently running and when the last sync completed."""
        db = SessionLocal()
        try:
            return json.dumps(_get_sync_status_impl(db))
        finally:
            db.close()

    @mcp.tool()
    def get_sync_history(limit: int = 10) -> str:
        """Get the last N sync runs with status, timing, and record counts."""
        db = SessionLocal()
        try:
            return json.dumps(_get_sync_history_impl(db, limit))
        finally:
            db.close()
```

**Step 4: Run tests to verify they pass**

```bash
cd backend && python3 -m pytest tests/test_mcp_sync.py -v
```
Expected: all 4 tests pass.

**Step 5: Commit**

```bash
git add backend/mcp/tools/sync.py backend/tests/test_mcp_sync.py
git commit -m "feat(mcp): add sync action tools with tests"
```

---

## Task 6: Wire up the MCP server

**Files:**
- Create: `backend/mcp/server.py`

**Step 1: Write a smoke test**

Create `backend/tests/test_mcp_server.py`:
```python
from mcp.server import create_mcp_app
from starlette.testclient import TestClient


def test_mcp_app_returns_401_without_token():
    app = create_mcp_app(api_key="testsecret")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/mcp/")
    assert response.status_code == 401


def test_mcp_app_accessible_with_token():
    app = create_mcp_app(api_key="testsecret")
    client = TestClient(app, raise_server_exceptions=False)
    # Any request with valid bearer token should not get 401
    response = client.post("/mcp/", headers={"Authorization": "Bearer testsecret"}, json={})
    assert response.status_code != 401
```

**Step 2: Run test to verify it fails**

```bash
cd backend && python3 -m pytest tests/test_mcp_server.py -v
```
Expected: `ImportError`.

**Step 3: Implement server.py**

Create `backend/mcp/server.py`:
```python
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Mount

from mcp.auth import BearerAuthMiddleware
from mcp.tools.notes import register_note_tools
from mcp.tools.reports import register_report_tools
from mcp.tools.sync import register_sync_tools


def create_mcp_app(api_key: str):
    """Create the MCP ASGI app with bearer auth. api_key is required."""
    server = FastMCP("Notes HQ")

    register_note_tools(server)
    register_report_tools(server)
    register_sync_tools(server)

    raw_app = server.streamable_http_app()

    return Starlette(
        routes=[Mount("/mcp", app=raw_app)],
        middleware=[Middleware(BearerAuthMiddleware, api_key=api_key)],
    )
```

**Step 4: Run test to verify it passes**

```bash
cd backend && python3 -m pytest tests/test_mcp_server.py -v
```
Expected: both tests pass.

**Step 5: Commit**

```bash
git add backend/mcp/server.py backend/tests/test_mcp_server.py
git commit -m "feat(mcp): wire up FastMCP server with auth and all tools"
```

---

## Task 7: Mount MCP server in FastAPI

**Files:**
- Modify: `backend/app/main.py`

**Step 1: Add the mount to main.py**

In `backend/app/main.py`, add two imports at the top of the file (after existing imports):
```python
from mcp.server import create_mcp_app
from app.config import get_settings
```

Then add the mount AFTER the router includes and BEFORE the `if FRONTEND_DIR.exists():` block:
```python
# Mount MCP server (before the frontend catch-all route)
_settings = get_settings()
if _settings.mcp_api_key:
    app.mount("/mcp", create_mcp_app(api_key=_settings.mcp_api_key))
```

The complete relevant section of main.py should look like:
```python
# Include routers
app.include_router(sync.router, prefix="/api/v1")
app.include_router(notes.router, prefix="/api/v1")
app.include_router(features.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(scheduler.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Mount MCP server (before the frontend catch-all route)
_settings = get_settings()
if _settings.mcp_api_key:
    app.mount("/mcp", create_mcp_app(api_key=_settings.mcp_api_key))


# Serve frontend static files (if built)
if FRONTEND_DIR.exists():
    ...
```

**Step 2: Smoke test the full app starts**

```bash
cd backend && MCP_API_KEY=testsecret python3 -c "from app.main import app; print('app loaded ok')"
```
Expected: `app loaded ok`

**Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(mcp): mount MCP server at /mcp in FastAPI app"
```

---

## Task 8: Run all MCP tests end-to-end

**Step 1: Run the full MCP test suite**

```bash
cd backend && python3 -m pytest tests/test_mcp_auth.py tests/test_mcp_notes.py tests/test_mcp_reports.py tests/test_mcp_sync.py tests/test_mcp_server.py -v
```
Expected: all tests pass.

**Step 2: Quick manual smoke test with curl**

Start the server locally:
```bash
cd backend && MCP_API_KEY=testsecret DATABASE_URL=sqlite:///./pdb_insights.db uvicorn app.main:app --port 8000
```

In another terminal, verify auth works:
```bash
# Should get 401
curl -s http://localhost:8000/mcp/ | python3 -m json.tool

# Should get a non-401 response
curl -s -X POST http://localhost:8000/mcp/ \
  -H "Authorization: Bearer testsecret" \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool
```

**Step 3: Commit (if any fixes were needed)**

```bash
git add -p
git commit -m "fix(mcp): address issues found during smoke test"
```

---

## Task 9: Deploy to fly.io

**Step 1: Set the MCP API key secret**

```bash
fly secrets set MCP_API_KEY=<your-secret-token> --app notes-hq
```
Use a strong random token (e.g., `openssl rand -hex 32`).

**Step 2: Deploy**

```bash
fly deploy --app notes-hq
```
Expected: deployment succeeds.

**Step 3: Verify the endpoint is live**

```bash
# Should get 401 (confirms endpoint exists)
curl -s https://notes-hq.fly.dev/mcp/

# Should get a valid MCP response
curl -s -X POST https://notes-hq.fly.dev/mcp/ \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{}' | head -c 200
```

**Step 4: Connect Claude.ai**

1. Go to Claude.ai → Settings → Integrations → Add MCP Server
2. URL: `https://notes-hq.fly.dev/mcp`
3. Auth type: Bearer token
4. Token: paste your `MCP_API_KEY` value
5. Verify tools appear in Claude.ai

---

## Reference: Final Tool List

| # | Tool | Category |
|---|------|----------|
| 1 | `list_notes` | Query |
| 2 | `get_note` | Query |
| 3 | `search_notes` | Query |
| 4 | `get_notes_stats` | Query |
| 5 | `list_members` | Query |
| 6 | `list_companies` | Query |
| 7 | `list_features` | Query |
| 8 | `get_notes_insights` | Analytics |
| 9 | `get_notes_trend` | Analytics |
| 10 | `get_response_time_stats` | Analytics |
| 11 | `get_sla_report` | Analytics |
| 12 | `get_pm_workload` | Analytics |
| 13 | `trigger_sync` | Action |
| 14 | `get_sync_status` | Action |
| 15 | `get_sync_history` | Action |
