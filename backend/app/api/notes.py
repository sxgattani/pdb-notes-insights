from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Note, Member, Company, NoteFeature, Feature, NoteComment

router = APIRouter(prefix="/notes", tags=["notes"])


def _calculate_response_time(note: Note) -> Optional[float]:
    """Calculate response time in days (processed_at - created_at)."""
    if note.processed_at and note.created_at:
        delta = note.processed_at - note.created_at
        return round(delta.total_seconds() / 86400, 1)
    return None


@router.get("")
def list_notes(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    state: Optional[str] = None,
    owner_id: Optional[int] = None,
    unassigned: Optional[bool] = None,
    creator_id: Optional[int] = None,
    company_id: Optional[int] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    updated_after: Optional[str] = None,
    updated_before: Optional[str] = None,
    group_by: Optional[str] = None,
    sort: str = "created_at",
    order: str = "desc",
    db: Session = Depends(get_db),
):
    """List notes with filtering, grouping, and pagination."""
    query = db.query(Note).filter(Note.deleted_at.is_(None))  # Exclude soft-deleted

    # Filters
    if state:
        query = query.filter(Note.state == state)
    if unassigned:
        query = query.filter(Note.owner_id.is_(None))
    elif owner_id:
        query = query.filter(Note.owner_id == owner_id)
    if creator_id:
        query = query.filter(Note.created_by_id == creator_id)
    if company_id:
        query = query.filter(Note.company_id == company_id)

    # Date range filters
    # For "before" dates, add 1 day to include the entire day (since date strings are interpreted as midnight)
    if created_after:
        query = query.filter(Note.created_at >= created_after)
    if created_before:
        # Add 1 day to include all notes created on the specified date
        created_before_dt = datetime.strptime(created_before, "%Y-%m-%d") + timedelta(days=1)
        query = query.filter(Note.created_at < created_before_dt)
    if updated_after:
        query = query.filter(Note.updated_at >= updated_after)
    if updated_before:
        # Add 1 day to include all notes updated on the specified date
        updated_before_dt = datetime.strptime(updated_before, "%Y-%m-%d") + timedelta(days=1)
        query = query.filter(Note.updated_at < updated_before_dt)

    # Sorting - handle both direct columns and related fields
    if sort == "company":
        query = query.outerjoin(Company, Note.company_id == Company.id)
        sort_expr = func.coalesce(Company.name, '')
    elif sort == "owner":
        query = query.outerjoin(Member, Note.owner_id == Member.id)
        sort_expr = func.coalesce(Member.name, Member.email, '')
    elif sort == "response_time":
        # Sort by response time (processed_at - created_at), nulls last
        sort_expr = func.julianday(Note.processed_at) - func.julianday(Note.created_at)
    else:
        sort_expr = getattr(Note, sort, Note.created_at)

    if order == "desc":
        query = query.order_by(sort_expr.desc())
    else:
        query = query.order_by(sort_expr.asc())

    # Calculate group counts BEFORE pagination (using the filtered query)
    group_counts = None
    if group_by and group_by in ['owner', 'creator', 'company']:
        # Build a separate query for counting by group
        if group_by == 'owner':
            count_query = (
                db.query(
                    func.coalesce(Member.name, Member.email, 'Unassigned').label('group_name'),
                    func.count(Note.id).label('count')
                )
                .select_from(Note)
                .outerjoin(Member, Note.owner_id == Member.id)
            )
        elif group_by == 'creator':
            count_query = (
                db.query(
                    func.coalesce(Member.name, Member.email, 'Unknown').label('group_name'),
                    func.count(Note.id).label('count')
                )
                .select_from(Note)
                .outerjoin(Member, Note.created_by_id == Member.id)
            )
        elif group_by == 'company':
            count_query = (
                db.query(
                    func.coalesce(Company.name, 'No Company').label('group_name'),
                    func.count(Note.id).label('count')
                )
                .select_from(Note)
                .outerjoin(Company, Note.company_id == Company.id)
            )

        # Apply the same filters to the count query
        count_query = count_query.filter(Note.deleted_at.is_(None))  # Exclude soft-deleted
        if state:
            count_query = count_query.filter(Note.state == state)
        if unassigned:
            count_query = count_query.filter(Note.owner_id.is_(None))
        elif owner_id:
            count_query = count_query.filter(Note.owner_id == owner_id)
        if creator_id:
            count_query = count_query.filter(Note.created_by_id == creator_id)
        if company_id:
            count_query = count_query.filter(Note.company_id == company_id)
        if created_after:
            count_query = count_query.filter(Note.created_at >= created_after)
        if created_before:
            created_before_dt = datetime.strptime(created_before, "%Y-%m-%d") + timedelta(days=1)
            count_query = count_query.filter(Note.created_at < created_before_dt)
        if updated_after:
            count_query = count_query.filter(Note.updated_at >= updated_after)
        if updated_before:
            updated_before_dt = datetime.strptime(updated_before, "%Y-%m-%d") + timedelta(days=1)
            count_query = count_query.filter(Note.updated_at < updated_before_dt)

        # Group and get counts
        count_results = count_query.group_by('group_name').all()
        group_counts = {name or ('Unassigned' if group_by == 'owner' else 'Unknown' if group_by == 'creator' else 'No Company'): count for name, count in count_results}

    # Pagination
    total = query.count()
    notes = query.offset((page - 1) * limit).limit(limit).all()

    # Convert to dicts with relationships
    notes_data = [_note_to_dict(n, db) for n in notes]

    # Group paginated results for display
    grouped_data = None
    if group_by and group_by in ['owner', 'creator', 'company']:
        grouped_data = {}
        for note in notes_data:
            if group_by == 'owner':
                key = note.get('owner', {}).get('name', 'Unassigned') if note.get('owner') else 'Unassigned'
            elif group_by == 'creator':
                key = note.get('creator', {}).get('name', 'Unknown') if note.get('creator') else 'Unknown'
            elif group_by == 'company':
                key = note.get('company', {}).get('name', 'No Company') if note.get('company') else 'No Company'
            else:
                key = 'Other'

            if key not in grouped_data:
                grouped_data[key] = []
            grouped_data[key].append(note)

    return {
        "data": notes_data,
        "grouped_data": grouped_data,
        "group_counts": group_counts,
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
    # Base query excluding soft-deleted notes
    base_query = db.query(Note).filter(Note.deleted_at.is_(None))

    total = base_query.count()
    processed = base_query.filter(Note.state == "processed").count()
    unprocessed = base_query.filter(Note.state == "unprocessed").count()

    # Notes by source_origin
    by_source = (
        db.query(Note.source_origin, func.count(Note.id))
        .filter(Note.deleted_at.is_(None))
        .group_by(Note.source_origin)
        .all()
    )

    # Calculate average response time for processed notes
    processed_notes = db.query(Note).filter(
        Note.deleted_at.is_(None),
        Note.state == "processed",
        Note.processed_at.isnot(None),
        Note.created_at.isnot(None)
    ).all()

    response_times = [_calculate_response_time(n) for n in processed_notes]
    response_times = [r for r in response_times if r is not None]
    avg_response_time = round(sum(response_times) / len(response_times), 1) if response_times else None

    return {
        "total": total,
        "processed": processed,
        "unprocessed": unprocessed,
        "avg_response_time_days": avg_response_time,
        "by_source": {s: c for s, c in by_source if s},
    }


@router.get("/filter-options")
def get_filter_options(db: Session = Depends(get_db)):
    """Get available filter options (members, companies, states)."""
    # Get members who are owners (excluding soft-deleted notes)
    owners = (
        db.query(Member.id, Member.name, Member.email)
        .join(Note, Note.owner_id == Member.id)
        .filter(Note.deleted_at.is_(None))
        .distinct()
        .all()
    )
    # Get members who are creators (excluding soft-deleted notes)
    creators = (
        db.query(Member.id, Member.name, Member.email)
        .join(Note, Note.created_by_id == Member.id)
        .filter(Note.deleted_at.is_(None))
        .distinct()
        .all()
    )

    # Get companies with notes (excluding soft-deleted notes)
    companies = (
        db.query(Company.id, Company.name)
        .join(Note, Note.company_id == Company.id)
        .filter(Note.deleted_at.is_(None))
        .distinct()
        .order_by(Company.name)
        .all()
    )

    # Get distinct states (excluding soft-deleted notes)
    states = db.query(Note.state).filter(Note.deleted_at.is_(None)).distinct().all()

    return {
        "owners": [{"id": u.id, "name": u.name or u.email} for u in owners],
        "creators": [{"id": u.id, "name": u.name or u.email} for u in creators],
        "companies": [{"id": c.id, "name": c.name} for c in companies],
        "states": [s[0] for s in states if s[0]],
    }


@router.get("/{note_id}")
def get_note(note_id: int, db: Session = Depends(get_db)):
    """Get a single note with relationships."""
    note = db.query(Note).filter(Note.id == note_id, Note.deleted_at.is_(None)).first()

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Get linked features
    feature_links = (
        db.query(Feature, NoteFeature.importance)
        .join(NoteFeature)
        .filter(NoteFeature.note_id == note_id)
        .all()
    )

    # Get comments
    comments = (
        db.query(NoteComment)
        .filter(NoteComment.note_id == note_id)
        .order_by(NoteComment.timestamp.desc())
        .limit(5)
        .all()
    )

    result = _note_to_dict(note, db)
    result["features"] = [
        {
            "id": f.id,
            "pb_id": f.pb_id,
            "name": f.name,
            "display_url": f.display_url,
            "importance": importance
        }
        for f, importance in feature_links
    ]
    result["comments"] = [
        {
            "id": c.id,
            "content": c.content,
            "timestamp": c.timestamp.isoformat() if c.timestamp else None,
            "member": _member_to_dict(db.query(Member).filter(Member.id == c.member_id).first()) if c.member_id else None
        }
        for c in comments
    ]

    return result


def _member_to_dict(member: Optional[Member]) -> Optional[dict]:
    """Convert Member model to dict."""
    if not member:
        return None
    return {
        "id": member.id,
        "name": member.name,
        "email": member.email
    }


def _note_to_dict(note: Note, db: Session = None) -> dict:
    """Convert Note model to dict with relationships."""
    result = {
        "id": note.id,
        "pb_id": note.pb_id,
        "title": note.title,
        "content": note.content,
        "state": note.state,
        "source_origin": note.source_origin,
        "display_url": note.display_url,
        "external_display_url": note.external_display_url,
        "tags": note.tags or [],
        "followers_count": note.followers_count or 0,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        "processed_at": note.processed_at.isoformat() if note.processed_at else None,
        "response_time_days": _calculate_response_time(note),
        "owner_id": note.owner_id,
        "created_by_id": note.created_by_id,
        "company_id": note.company_id,
    }

    # Include relationships if db session provided
    if db:
        if note.owner_id:
            owner = db.query(Member).filter(Member.id == note.owner_id).first()
            result["owner"] = _member_to_dict(owner)
        else:
            result["owner"] = None

        if note.created_by_id:
            creator = db.query(Member).filter(Member.id == note.created_by_id).first()
            result["creator"] = _member_to_dict(creator)
        else:
            result["creator"] = None

        if note.company_id:
            company = db.query(Company).filter(Company.id == note.company_id).first()
            result["company"] = {"id": company.id, "name": company.name} if company else None
        else:
            result["company"] = None

    return result
