import asyncio
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db, SessionLocal
from app.services.sync import SyncOrchestrator
from app.models import SyncHistory
from app.api.dependencies import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])

# Minimum time between syncs (in minutes)
MIN_SYNC_INTERVAL_MINUTES = 30


def _is_sync_running(db: Session) -> bool:
    """Check if a sync is currently running."""
    running = (
        db.query(SyncHistory)
        .filter(SyncHistory.status == "running")
        .first()
    )
    return running is not None


def _get_last_completed_sync(db: Session) -> SyncHistory | None:
    """Get the most recent completed sync."""
    return (
        db.query(SyncHistory)
        .filter(SyncHistory.status.in_(["completed", "partial"]))
        .order_by(desc(SyncHistory.completed_at))
        .first()
    )


def _should_sync(db: Session) -> tuple[bool, str]:
    """Check if a sync should be triggered. Returns (should_sync, reason)."""
    if _is_sync_running(db):
        return False, "Sync already in progress"

    last_sync = _get_last_completed_sync(db)
    if last_sync and last_sync.completed_at:
        # Make sure we compare timezone-aware datetimes
        completed_at = last_sync.completed_at
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)

        time_since_sync = datetime.now(timezone.utc) - completed_at
        if time_since_sync < timedelta(minutes=MIN_SYNC_INTERVAL_MINUTES):
            return False, f"Sync completed {int(time_since_sync.total_seconds() // 60)} minutes ago"

    return True, "Sync needed"


async def _run_sync():
    """Run the sync process."""
    db = SessionLocal()
    try:
        logger.info("Starting sync...")
        orchestrator = SyncOrchestrator(db)
        result = await orchestrator.run_full_sync()
        logger.info(f"Sync completed: {result}")
    except Exception as e:
        logger.exception(f"Sync failed: {e}")
    finally:
        db.close()


@router.post("/trigger")
async def trigger_sync(
    username: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Trigger an on-demand sync. Returns error if sync already running."""
    if _is_sync_running(db):
        return {"message": "Sync already in progress", "status": "running", "triggered": False}

    asyncio.create_task(_run_sync())
    return {"message": "Sync triggered", "status": "running", "triggered": True}


@router.post("/trigger-if-needed")
async def trigger_sync_if_needed(
    username: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Trigger a sync only if not already running and not synced recently."""
    should_sync, reason = _should_sync(db)

    if not should_sync:
        return {"message": reason, "status": "skipped", "triggered": False}

    asyncio.create_task(_run_sync())
    return {"message": "Sync triggered", "status": "running", "triggered": True}


@router.get("/status")
def get_sync_status(db: Session = Depends(get_db)):
    """Get current sync status including last completed sync time."""
    running = (
        db.query(SyncHistory)
        .filter(SyncHistory.status == "running")
        .first()
    )

    last_sync = _get_last_completed_sync(db)
    last_sync_at = last_sync.completed_at.isoformat() if last_sync and last_sync.completed_at else None

    if running:
        return {
            "status": "running",
            "entity_type": running.entity_type,
            "started_at": running.started_at.isoformat() if running.started_at else None,
            "last_sync_at": last_sync_at,
        }

    return {
        "status": "idle",
        "last_sync_at": last_sync_at,
    }


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
