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
