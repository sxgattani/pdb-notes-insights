import logging
from datetime import datetime

from app.database import SessionLocal
from app.config import get_settings
from app.services.sync.orchestrator import SyncOrchestrator
from app.scheduler import get_scheduler

logger = logging.getLogger(__name__)


async def run_sync_job():
    """Run the ProductBoard sync job."""
    logger.info(f"Starting scheduled sync at {datetime.utcnow().isoformat()}")

    db = SessionLocal()
    try:
        orchestrator = SyncOrchestrator(db)
        results = await orchestrator.run_full_sync()
        logger.info(f"Sync completed: {results}")
    except Exception as e:
        logger.error(f"Sync job failed: {e}")
        raise
    finally:
        db.close()


def register_sync_job():
    """Register the sync job with the scheduler."""
    settings = get_settings()

    if not settings.sync_enabled:
        logger.info("Sync is disabled, not registering sync job")
        return

    scheduler = get_scheduler()

    # Add interval job - runs every N hours
    scheduler.add_job(
        run_sync_job,
        'interval',
        hours=settings.sync_interval_hours,
        id='productboard_sync',
        name='ProductBoard Sync',
        replace_existing=True,
    )

    logger.info(f"Sync job registered: every {settings.sync_interval_hours} hours")
