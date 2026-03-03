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
