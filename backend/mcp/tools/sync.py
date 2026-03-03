import asyncio
import json
import logging
from datetime import timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import SyncHistory
from app.database import SessionLocal

logger = logging.getLogger(__name__)

_background_tasks: set = set()


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
            sdb = SessionLocal()
            try:
                orchestrator = SyncOrchestrator(sdb)
                await orchestrator.run_full_sync()
            except Exception as e:
                logger.exception(f"MCP-triggered sync failed: {e}")
            finally:
                sdb.close()

        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(_run())
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
        except RuntimeError:
            # No running event loop — shouldn't happen in FastAPI context
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
