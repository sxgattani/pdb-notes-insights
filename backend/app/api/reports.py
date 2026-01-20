from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer, and_, extract

from app.database import get_db
from app.models import Note, Member, Feature, Company

SLA_DAYS = 5  # Notes should be processed within 5 days

router = APIRouter(prefix="/reports", tags=["reports"])


def _calculate_response_time(note: Note) -> Optional[float]:
    """Calculate response time in days (processed_at - created_at)."""
    if note.processed_at and note.created_at:
        delta = note.processed_at - note.created_at
        return round(delta.total_seconds() / 86400, 1)
    return None


@router.get("/notes-insights")
def get_notes_insights(
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get notes insights dashboard data."""
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)
    previous_period_start = period_start - timedelta(days=days)

    # Current period stats
    current_total = (
        db.query(func.count(Note.id))
        .filter(Note.created_at >= period_start)
        .scalar() or 0
    )
    current_processed = (
        db.query(func.count(Note.id))
        .filter(Note.created_at >= period_start)
        .filter(Note.state == "processed")
        .scalar() or 0
    )
    current_unprocessed = (
        db.query(func.count(Note.id))
        .filter(Note.created_at >= period_start)
        .filter(Note.state == "unprocessed")
        .scalar() or 0
    )
    current_unassigned = (
        db.query(func.count(Note.id))
        .filter(Note.created_at >= period_start)
        .filter(Note.owner_id.is_(None))
        .scalar() or 0
    )

    # Previous period stats (for comparison)
    prev_total = (
        db.query(func.count(Note.id))
        .filter(Note.created_at >= previous_period_start)
        .filter(Note.created_at < period_start)
        .scalar() or 0
    )
    prev_processed = (
        db.query(func.count(Note.id))
        .filter(Note.created_at >= previous_period_start)
        .filter(Note.created_at < period_start)
        .filter(Note.state == "processed")
        .scalar() or 0
    )
    prev_unprocessed = (
        db.query(func.count(Note.id))
        .filter(Note.created_at >= previous_period_start)
        .filter(Note.created_at < period_start)
        .filter(Note.state == "unprocessed")
        .scalar() or 0
    )
    prev_unassigned = (
        db.query(func.count(Note.id))
        .filter(Note.created_at >= previous_period_start)
        .filter(Note.created_at < period_start)
        .filter(Note.owner_id.is_(None))
        .scalar() or 0
    )

    def calc_change(current: int, previous: int) -> Optional[float]:
        if previous == 0:
            return None if current == 0 else 100.0
        return round(((current - previous) / previous) * 100, 1)

    # Calculate average response time for current period
    processed_notes_current = db.query(Note).filter(
        Note.created_at >= period_start,
        Note.state == "processed",
        Note.processed_at.isnot(None)
    ).all()
    response_times_current = [_calculate_response_time(n) for n in processed_notes_current]
    response_times_current = [r for r in response_times_current if r is not None]
    avg_response_time = round(sum(response_times_current) / len(response_times_current), 1) if response_times_current else None

    # Calculate average response time for previous period
    processed_notes_prev = db.query(Note).filter(
        Note.created_at >= previous_period_start,
        Note.created_at < period_start,
        Note.state == "processed",
        Note.processed_at.isnot(None)
    ).all()
    response_times_prev = [_calculate_response_time(n) for n in processed_notes_prev]
    response_times_prev = [r for r in response_times_prev if r is not None]
    avg_response_time_prev = round(sum(response_times_prev) / len(response_times_prev), 1) if response_times_prev else None

    def calc_change_float(current: Optional[float], previous: Optional[float]) -> Optional[float]:
        if current is None or previous is None or previous == 0:
            return None
        return round(((current - previous) / previous) * 100, 1)

    # SLA threshold for owner stats
    sla_threshold = now - timedelta(days=SLA_DAYS)

    # Notes by owner with stats
    owners_query = (
        db.query(
            Member.id,
            Member.name,
            Member.email,
            func.count(Note.id).label("assigned"),
            func.sum(func.cast(Note.state == "processed", Integer)).label("processed"),
            func.sum(func.cast(Note.state == "unprocessed", Integer)).label("unprocessed"),
        )
        .join(Note, Note.owner_id == Member.id)
        .filter(Note.created_at >= period_start)
        .group_by(Member.id, Member.name, Member.email)
        .all()
    )

    # Get SLA breached count per owner
    sla_breached_by_owner = dict(
        db.query(Note.owner_id, func.count(Note.id))
        .filter(Note.state == "unprocessed")
        .filter(Note.created_at < sla_threshold)
        .group_by(Note.owner_id)
        .all()
    )

    # Get average response time per owner
    owner_response_times = defaultdict(list)
    for note in processed_notes_current:
        if note.owner_id:
            rt = _calculate_response_time(note)
            if rt is not None:
                owner_response_times[note.owner_id].append(rt)

    owners = []
    for member_id, name, email, assigned, processed, unprocessed in owners_query:
        assigned = assigned or 0
        processed = processed or 0
        unprocessed = unprocessed or 0
        progress = round((processed / assigned * 100), 0) if assigned > 0 else 0

        # Calculate avg response time for this owner
        owner_rts = owner_response_times.get(member_id, [])
        owner_avg_rt = round(sum(owner_rts) / len(owner_rts), 1) if owner_rts else None

        owners.append({
            "id": member_id,
            "name": name or email or "Unknown",
            "email": email,
            "assigned": assigned,
            "processed": processed,
            "unprocessed": unprocessed,
            "progress": progress,
            "avg_response_time": owner_avg_rt,
            "sla_breached": sla_breached_by_owner.get(member_id, 0),
        })

    # Sort by assigned descending
    owners.sort(key=lambda x: x["assigned"], reverse=True)

    return {
        "period_days": days,
        "summary": {
            "created": {
                "value": current_total,
                "change": calc_change(current_total, prev_total),
            },
            "processed": {
                "value": current_processed,
                "change": calc_change(current_processed, prev_processed),
            },
            "unprocessed": {
                "value": current_unprocessed,
                "change": calc_change(current_unprocessed, prev_unprocessed),
            },
            "unassigned": {
                "value": current_unassigned,
                "change": calc_change(current_unassigned, prev_unassigned),
            },
            "avg_response_time": {
                "value": avg_response_time,
                "change": calc_change_float(avg_response_time, avg_response_time_prev),
            },
        },
        "by_owner": owners,
    }


@router.get("/notes-trend")
def get_notes_trend(
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get weekly notes trend (created vs processed)."""
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)

    # Get all notes in period
    notes = db.query(Note).filter(Note.created_at >= period_start).all()

    # Group by week
    weekly_created = defaultdict(int)
    weekly_processed = defaultdict(int)

    for note in notes:
        if note.created_at:
            week = note.created_at.isocalendar()
            week_key = f"{week.year}-W{week.week:02d}"
            weekly_created[week_key] += 1

            if note.state == "processed":
                weekly_processed[week_key] += 1

    # Build sorted result
    all_weeks = sorted(set(weekly_created.keys()) | set(weekly_processed.keys()))
    data = [
        {
            "week": week,
            "created": weekly_created.get(week, 0),
            "processed": weekly_processed.get(week, 0),
        }
        for week in all_weeks
    ]

    return {"data": data}


@router.get("/response-time")
def get_response_time_stats(
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get response time analytics."""
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)

    # Get all processed notes with response times
    processed_notes = db.query(Note).filter(
        Note.created_at >= period_start,
        Note.state == "processed",
        Note.processed_at.isnot(None)
    ).all()

    response_times = []
    for note in processed_notes:
        rt = _calculate_response_time(note)
        if rt is not None:
            response_times.append({"note": note, "rt": rt})

    if not response_times:
        return {
            "average_days": None,
            "median_days": None,
            "distribution": [],
            "by_owner": [],
        }

    # Calculate stats
    rts = [r["rt"] for r in response_times]
    rts.sort()
    avg = round(sum(rts) / len(rts), 1)
    median = rts[len(rts) // 2]

    # Distribution buckets
    buckets = {"<1 day": 0, "1-3 days": 0, "3-5 days": 0, "5+ days": 0}
    for rt in rts:
        if rt < 1:
            buckets["<1 day"] += 1
        elif rt < 3:
            buckets["1-3 days"] += 1
        elif rt < 5:
            buckets["3-5 days"] += 1
        else:
            buckets["5+ days"] += 1

    distribution = [{"bucket": k, "count": v} for k, v in buckets.items()]

    # By owner
    owner_data = defaultdict(list)
    for r in response_times:
        if r["note"].owner_id:
            owner_data[r["note"].owner_id].append(r["rt"])

    by_owner = []
    for owner_id, owner_rts in owner_data.items():
        member = db.query(Member).filter(Member.id == owner_id).first()
        if member:
            by_owner.append({
                "id": owner_id,
                "name": member.name or member.email or "Unknown",
                "avg_response_time": round(sum(owner_rts) / len(owner_rts), 1),
                "count": len(owner_rts),
            })

    by_owner.sort(key=lambda x: x["avg_response_time"])

    return {
        "average_days": avg,
        "median_days": median,
        "distribution": distribution,
        "by_owner": by_owner,
    }


@router.get("/workload")
def get_pm_workload(db: Session = Depends(get_db)):
    """Get workload statistics per PM (member)."""
    # Get note counts per owner
    note_stats = (
        db.query(
            Member.id,
            Member.name,
            Member.email,
            func.count(Note.id).label("total_notes"),
            func.sum(func.cast(Note.state == "unprocessed", Integer)).label("unprocessed_notes"),
            func.sum(func.cast(Note.state == "processed", Integer)).label("processed_notes"),
        )
        .outerjoin(Note, Note.owner_id == Member.id)
        .group_by(Member.id, Member.name, Member.email)
        .all()
    )

    workload = []
    for member_id, name, email, total_notes, unprocessed, processed in note_stats:
        workload.append({
            "user_id": member_id,
            "name": name or email or "Unknown",
            "email": email,
            "total_notes": total_notes or 0,
            "unprocessed_notes": unprocessed or 0,
            "processed_notes": processed or 0,
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
    member = db.query(Member).filter(Member.id == user_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

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
            "id": member.id,
            "name": member.name,
            "email": member.email,
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
def get_sla_report(
    days: int = Query(None, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get SLA compliance report for notes processing."""
    now = datetime.utcnow()
    sla_threshold = now - timedelta(days=SLA_DAYS)

    # Build query for unprocessed notes
    query = db.query(Note).filter(Note.state == "unprocessed")

    # Filter by created_at if days parameter is provided
    if days is not None:
        period_start = now - timedelta(days=days)
        query = query.filter(Note.created_at >= period_start)

    unprocessed_notes = query.all()

    at_risk = []  # Within 1 day of SLA breach
    breached = []  # Past SLA deadline
    on_track = []  # More than 1 day until SLA deadline

    warning_threshold = now - timedelta(days=SLA_DAYS - 1)

    # Pre-fetch owners and companies for efficiency
    owner_ids = {n.owner_id for n in unprocessed_notes if n.owner_id}
    company_ids = {n.company_id for n in unprocessed_notes if n.company_id}

    owners_map = {}
    if owner_ids:
        owners = db.query(Member).filter(Member.id.in_(owner_ids)).all()
        owners_map = {m.id: m.name or m.email or "Unknown" for m in owners}

    companies_map = {}
    if company_ids:
        companies = db.query(Company).filter(Company.id.in_(company_ids)).all()
        companies_map = {c.id: c.name or "Unknown" for c in companies}

    for note in unprocessed_notes:
        if not note.created_at:
            continue

        note_data = {
            "id": note.id,
            "title": note.title,
            "created_at": note.created_at.isoformat(),
            "days_old": (now - note.created_at).days,
            "owner_id": note.owner_id,
            "owner_name": owners_map.get(note.owner_id) if note.owner_id else None,
            "company_id": note.company_id,
            "company_name": companies_map.get(note.company_id) if note.company_id else None,
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

    # SLA by owner
    owner_sla = defaultdict(lambda: {"breached": 0, "at_risk": 0, "on_track": 0})
    for note in breached:
        owner_sla[note["owner_id"]]["breached"] += 1
    for note in at_risk:
        owner_sla[note["owner_id"]]["at_risk"] += 1
    for note in on_track:
        owner_sla[note["owner_id"]]["on_track"] += 1

    by_owner = []
    for owner_id, stats in owner_sla.items():
        if owner_id:
            member = db.query(Member).filter(Member.id == owner_id).first()
            total = stats["breached"] + stats["at_risk"] + stats["on_track"]
            by_owner.append({
                "id": owner_id,
                "name": member.name or member.email if member else "Unknown",
                "breached": stats["breached"],
                "at_risk": stats["at_risk"],
                "on_track": stats["on_track"],
                "compliance_rate": round((1 - stats["breached"] / max(total, 1)) * 100, 1),
            })

    by_owner.sort(key=lambda x: x["breached"], reverse=True)

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
        "by_owner": by_owner,
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
            Member.id,
            Member.name,
            Member.email,
            func.count(Note.id).label("breached_count"),
        )
        .join(Note, Note.owner_id == Member.id)
        .filter(Note.state == "unprocessed")
        .filter(Note.created_at < sla_threshold)
        .group_by(Member.id, Member.name, Member.email)
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
    for member_id, name, email, breached_count in breached_by_owner:
        total = unprocessed_by_owner.get(member_id, 0)
        result.append({
            "user_id": member_id,
            "name": name or email or "Unknown",
            "breached_count": breached_count,
            "total_unprocessed": total,
            "compliance_rate": round((1 - breached_count / max(total, 1)) * 100, 1),
        })

    # Sort by breached count descending
    result.sort(key=lambda x: x["breached_count"], reverse=True)

    return {"data": result}
