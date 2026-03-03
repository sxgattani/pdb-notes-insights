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


def _pct_change(cur: int, prev: int) -> Optional[float]:
    if prev == 0:
        return None if cur == 0 else 100.0
    return round(((cur - prev) / prev) * 100, 1)


def _get_notes_insights_impl(db: Session, days: int = 90) -> dict:
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)
    prev_start = period_start - timedelta(days=days)

    def count_where(*filters):
        q = db.query(func.count(Note.id)).filter(Note.deleted_at.is_(None))
        for f in filters:
            q = q.filter(f)
        return q.scalar() or 0

    cur_total = count_where(Note.created_at >= period_start)
    cur_processed = count_where(Note.created_at >= period_start, Note.state == "processed")
    cur_unprocessed = count_where(Note.created_at >= period_start, Note.state == "unprocessed")
    cur_unassigned = count_where(Note.created_at >= period_start, Note.owner_id.is_(None))

    prev_total = count_where(Note.created_at >= prev_start, Note.created_at < period_start)
    prev_processed = count_where(Note.created_at >= prev_start, Note.created_at < period_start, Note.state == "processed")
    prev_unprocessed = count_where(Note.created_at >= prev_start, Note.created_at < period_start, Note.state == "unprocessed")
    prev_unassigned = count_where(Note.created_at >= prev_start, Note.created_at < period_start, Note.owner_id.is_(None))

    # Avg response time current period
    proc_notes = db.query(Note).filter(
        Note.deleted_at.is_(None), Note.created_at >= period_start,
        Note.state == "processed", Note.processed_at.isnot(None)
    ).all()
    rts = [rt for n in proc_notes if (rt := _calc_rt(n)) is not None]
    avg_rt = round(sum(rts) / len(rts), 1) if rts else None

    # Avg response time previous period
    prev_proc = db.query(Note).filter(
        Note.deleted_at.is_(None), Note.created_at >= prev_start, Note.created_at < period_start,
        Note.state == "processed", Note.processed_at.isnot(None)
    ).all()
    prev_rts = [_calc_rt(n) for n in prev_proc if _calc_rt(n) is not None]
    prev_avg_rt = round(sum(prev_rts) / len(prev_rts), 1) if prev_rts else None

    rt_change = None
    if avg_rt is not None and prev_avg_rt is not None and prev_avg_rt != 0:
        rt_change = round(((avg_rt - prev_avg_rt) / prev_avg_rt) * 100, 1)

    # By owner
    sla_threshold = now - timedelta(days=SLA_DAYS)
    owner_rows = (
        db.query(Member.id, Member.name, Member.email, func.count(Note.id).label("assigned"))
        .join(Note, Note.owner_id == Member.id)
        .filter(Note.deleted_at.is_(None), Note.created_at >= period_start)
        .group_by(Member.id, Member.name, Member.email)
        .all()
    )
    sla_breached_map = dict(
        db.query(Note.owner_id, func.count(Note.id))
        .filter(Note.deleted_at.is_(None), Note.state == "unprocessed",
                Note.created_at >= period_start, Note.created_at < sla_threshold)
        .group_by(Note.owner_id).all()
    )
    processed_map = dict(
        db.query(Note.owner_id, func.count(Note.id))
        .filter(Note.deleted_at.is_(None), Note.created_at >= period_start, Note.state == "processed")
        .group_by(Note.owner_id).all()
    )
    unprocessed_map = dict(
        db.query(Note.owner_id, func.count(Note.id))
        .filter(Note.deleted_at.is_(None), Note.created_at >= period_start, Note.state == "unprocessed")
        .group_by(Note.owner_id).all()
    )
    owner_rts: dict = defaultdict(list)
    for n in proc_notes:
        if n.owner_id:
            rt = _calc_rt(n)
            if rt is not None:
                owner_rts[n.owner_id].append(rt)

    by_owner = []
    for mid, name, email, assigned in owner_rows:
        processed = processed_map.get(mid, 0)
        unprocessed = unprocessed_map.get(mid, 0)
        orts = owner_rts.get(mid, [])
        by_owner.append({
            "id": mid, "name": name or email or "Unknown",
            "assigned": assigned, "processed": processed, "unprocessed": unprocessed,
            "progress": round(processed / assigned * 100) if assigned else 0,
            "avg_response_time": round(sum(orts) / len(orts), 1) if orts else None,
            "sla_breached": sla_breached_map.get(mid, 0),
        })
    # Add unassigned notes to by_owner
    unassigned_assigned = count_where(Note.created_at >= period_start, Note.owner_id.is_(None))
    if unassigned_assigned > 0:
        unassigned_processed = count_where(Note.created_at >= period_start, Note.owner_id.is_(None), Note.state == "processed")
        unassigned_unprocessed = count_where(Note.created_at >= period_start, Note.owner_id.is_(None), Note.state == "unprocessed")
        by_owner.append({
            "id": None, "name": "Unassigned",
            "assigned": unassigned_assigned,
            "processed": unassigned_processed,
            "unprocessed": unassigned_unprocessed,
            "progress": round(unassigned_processed / unassigned_assigned * 100) if unassigned_assigned else 0,
            "avg_response_time": None,
            "sla_breached": sla_breached_map.get(None, 0),
        })
    by_owner.sort(key=lambda x: x["assigned"], reverse=True)

    return {
        "period_days": days,
        "summary": {
            "created": {"value": cur_total, "change": _pct_change(cur_total, prev_total)},
            "processed": {"value": cur_processed, "change": _pct_change(cur_processed, prev_processed)},
            "unprocessed": {"value": cur_unprocessed, "change": _pct_change(cur_unprocessed, prev_unprocessed)},
            "unassigned": {"value": cur_unassigned, "change": _pct_change(cur_unassigned, prev_unassigned)},
            "avg_response_time": {"value": avg_rt, "change": rt_change},
        },
        "by_owner": by_owner,
    }


def _get_notes_trend_impl(db: Session, days: int = 90) -> dict:
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)
    notes = db.query(Note).filter(Note.deleted_at.is_(None), Note.created_at >= period_start).all()
    weekly_created: dict = defaultdict(int)
    weekly_processed: dict = defaultdict(int)
    for note in notes:
        if note.created_at:
            w = note.created_at.isocalendar()
            key = f"{w[0]}-W{w[1]:02d}"
            weekly_created[key] += 1
            if note.state == "processed":
                weekly_processed[key] += 1
    all_weeks = sorted(set(weekly_created) | set(weekly_processed))
    return {
        "data": [
            {"week": w, "created": weekly_created.get(w, 0), "processed": weekly_processed.get(w, 0)}
            for w in all_weeks
        ]
    }


def _get_response_time_stats_impl(db: Session, days: int = 90) -> dict:
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)
    notes = db.query(Note).filter(
        Note.deleted_at.is_(None), Note.created_at >= period_start,
        Note.state == "processed", Note.processed_at.isnot(None)
    ).all()
    rts = [(n, rt) for n in notes if (rt := _calc_rt(n)) is not None]
    if not rts:
        return {"average_days": None, "median_days": None, "distribution": [], "by_owner": []}
    vals = sorted(r for _, r in rts)
    avg = round(sum(vals) / len(vals), 1)
    median = vals[len(vals) // 2]
    buckets = {"<1 day": 0, "1-3 days": 0, "3-5 days": 0, "5+ days": 0}
    for v in vals:
        if v < 1:
            buckets["<1 day"] += 1
        elif v < 3:
            buckets["1-3 days"] += 1
        elif v < 5:
            buckets["3-5 days"] += 1
        else:
            buckets["5+ days"] += 1
    owner_data: dict = defaultdict(list)
    for note, rt in rts:
        if note.owner_id:
            owner_data[note.owner_id].append(rt)
    owner_ids = set(owner_data.keys())
    members_map = {m.id: m for m in db.query(Member).filter(Member.id.in_(owner_ids)).all()} if owner_ids else {}
    by_owner = []
    for oid, orts in owner_data.items():
        m = members_map.get(oid)
        if m:
            by_owner.append({
                "id": oid, "name": m.name or m.email,
                "avg_response_time": round(sum(orts) / len(orts), 1),
                "count": len(orts),
            })
    by_owner.sort(key=lambda x: x["avg_response_time"])
    return {
        "average_days": avg,
        "median_days": median,
        "distribution": [{"bucket": k, "count": v} for k, v in buckets.items()],
        "by_owner": by_owner,
    }


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
    company_ids = {n.company_id for n in notes if n.company_id}
    owners_map = {m.id: m.name or m.email for m in db.query(Member).filter(Member.id.in_(owner_ids)).all()} if owner_ids else {}
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
            "breached": len(breached),
            "at_risk": len(at_risk),
            "on_track": len(on_track),
            "sla_compliance_rate": round((1 - len(breached) / max(len(notes), 1)) * 100, 1),
        },
        "breached_notes": breached[:50],
        "at_risk_notes": at_risk[:50],
        "sla_days": SLA_DAYS,
    }


def _get_pm_workload_impl(db: Session) -> dict:
    from sqlalchemy import case
    rows = (
        db.query(
            Member.id,
            Member.name,
            Member.email,
            func.count(Note.id).label("total"),
            func.sum(case((Note.state == "unprocessed", 1), else_=0)).label("unprocessed"),
            func.sum(case((Note.state == "processed", 1), else_=0)).label("processed"),
        )
        .outerjoin(Note, (Note.owner_id == Member.id) & (Note.deleted_at.is_(None)))
        .group_by(Member.id, Member.name, Member.email)
        .all()
    )
    workload = [
        {
            "id": mid, "name": name or email, "email": email,
            "total_notes": total or 0,
            "unprocessed_notes": unprocessed or 0,
            "processed_notes": processed or 0,
        }
        for mid, name, email, total, unprocessed, processed in rows
    ]
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
        """Get SLA compliance report: breached (>5 days unprocessed), at-risk, and on-track notes."""
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
