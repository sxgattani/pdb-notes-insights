from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.sync import SyncOrchestrator
from app.models import SyncHistory
from app.api.dependencies import require_auth

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/trigger")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    username: str = Depends(require_auth),
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
