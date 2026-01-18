from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer

from app.database import get_db
from app.models import Note, User, Feature

SLA_DAYS = 5  # Notes should be processed within 5 days

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


@router.get("/sla")
def get_sla_report(db: Session = Depends(get_db)):
    """Get SLA compliance report for notes processing."""
    now = datetime.utcnow()
    sla_threshold = now - timedelta(days=SLA_DAYS)

    # Get all unprocessed notes
    unprocessed_notes = (
        db.query(Note)
        .filter(Note.state == "unprocessed")
        .all()
    )

    at_risk = []  # Within 1 day of SLA breach
    breached = []  # Past SLA deadline
    on_track = []  # More than 1 day until SLA deadline

    warning_threshold = now - timedelta(days=SLA_DAYS - 1)

    for note in unprocessed_notes:
        if not note.created_at:
            continue

        note_data = {
            "id": note.id,
            "title": note.title,
            "created_at": note.created_at.isoformat(),
            "days_old": (now - note.created_at).days,
            "owner_id": note.owner_id,
        }

        if note.created_at < sla_threshold:
            breached.append(note_data)
        elif note.created_at < warning_threshold:
            at_risk.append(note_data)
        else:
            on_track.append(note_data)

    # Sort by age (oldest first for breached/at_risk)
    breached.sort(key=lambda x: x["days_old"], reverse=True)
    at_risk.sort(key=lambda x: x["days_old"], reverse=True)

    # Calculate metrics
    total_unprocessed = len(unprocessed_notes)

    return {
        "summary": {
            "total_unprocessed": total_unprocessed,
            "breached": len(breached),
            "at_risk": len(at_risk),
            "on_track": len(on_track),
            "sla_compliance_rate": round(
                (1 - len(breached) / max(total_unprocessed, 1)) * 100, 1
            ),
        },
        "breached_notes": breached[:50],  # Limit response size
        "at_risk_notes": at_risk[:50],
        "sla_days": SLA_DAYS,
    }


@router.get("/sla/by-owner")
def get_sla_by_owner(db: Session = Depends(get_db)):
    """Get SLA compliance breakdown by owner."""
    now = datetime.utcnow()
    sla_threshold = now - timedelta(days=SLA_DAYS)

    # Get breached counts per owner
    breached_by_owner = (
        db.query(
            User.id,
            User.name,
            User.email,
            func.count(Note.id).label("breached_count"),
        )
        .join(Note, Note.owner_id == User.id)
        .filter(Note.state == "unprocessed")
        .filter(Note.created_at < sla_threshold)
        .group_by(User.id, User.name, User.email)
        .all()
    )

    # Get total unprocessed per owner
    unprocessed_by_owner = dict(
        db.query(Note.owner_id, func.count(Note.id))
        .filter(Note.state == "unprocessed")
        .group_by(Note.owner_id)
        .all()
    )

    result = []
    for user_id, name, email, breached_count in breached_by_owner:
        total = unprocessed_by_owner.get(user_id, 0)
        result.append({
            "user_id": user_id,
            "name": name or email or "Unknown",
            "breached_count": breached_count,
            "total_unprocessed": total,
            "compliance_rate": round((1 - breached_count / max(total, 1)) * 100, 1),
        })

    # Sort by breached count descending
    result.sort(key=lambda x: x["breached_count"], reverse=True)

    return {"data": result}
