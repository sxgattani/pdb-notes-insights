from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer

from app.database import get_db
from app.models import Note, User, Feature

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/workload")
def get_pm_workload(db: Session = Depends(get_db)):
    """Get workload statistics per PM (user)."""
    # Get note counts per owner
    note_stats = (
        db.query(
            User.id,
            User.name,
            User.email,
            func.count(Note.id).label("total_notes"),
            func.sum(func.cast(Note.state == "unprocessed", Integer)).label("unprocessed_notes"),
            func.sum(func.cast(Note.state == "processed", Integer)).label("processed_notes"),
        )
        .outerjoin(Note, Note.owner_id == User.id)
        .group_by(User.id, User.name, User.email)
        .all()
    )

    # Get feature counts per owner
    feature_counts = dict(
        db.query(Feature.owner_id, func.count(Feature.id))
        .group_by(Feature.owner_id)
        .all()
    )

    workload = []
    for user_id, name, email, total_notes, unprocessed, processed in note_stats:
        workload.append({
            "user_id": user_id,
            "name": name or email or "Unknown",
            "email": email,
            "total_notes": total_notes or 0,
            "unprocessed_notes": unprocessed or 0,
            "processed_notes": processed or 0,
            "total_features": feature_counts.get(user_id, 0),
        })

    # Sort by unprocessed notes descending (highest workload first)
    workload.sort(key=lambda x: x["unprocessed_notes"], reverse=True)

    return {
        "data": workload,
        "summary": {
            "total_users": len(workload),
            "total_unprocessed": sum(w["unprocessed_notes"] for w in workload),
            "total_processed": sum(w["processed_notes"] for w in workload),
        }
    }


@router.get("/workload/{user_id}")
def get_user_workload(user_id: int, db: Session = Depends(get_db)):
    """Get detailed workload for a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user's notes
    notes = (
        db.query(Note)
        .filter(Note.owner_id == user_id)
        .order_by(Note.created_at.desc())
        .limit(50)
        .all()
    )

    unprocessed_notes = [n for n in notes if n.state == "unprocessed"]
    processed_notes = [n for n in notes if n.state == "processed"]

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
        "stats": {
            "total_notes": len(notes),
            "unprocessed": len(unprocessed_notes),
            "processed": len(processed_notes),
        },
        "recent_notes": [
            {
                "id": n.id,
                "title": n.title,
                "state": n.state,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notes[:20]
        ],
    }
