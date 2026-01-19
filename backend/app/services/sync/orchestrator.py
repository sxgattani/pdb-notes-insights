import logging
from sqlalchemy.orm import Session

from app.services.sync.members_syncer import MembersSyncer
from app.services.sync.notes_syncer import NotesSyncer

logger = logging.getLogger(__name__)


class SyncOrchestrator:
    """Orchestrates the sync of all entities in correct order."""

    def __init__(self, db: Session):
        self.db = db

    async def run_full_sync(self) -> dict:
        """
        Run a full sync of all entities in dependency order.

        Order:
        1. Members (from users API - gets PB member IDs)
        2. Notes (fetches companies on-demand, creates members on-the-fly)
        """
        results = {}

        # Phase 1: Members (from users API)
        try:
            logger.info("Syncing members...")
            members_syncer = MembersSyncer(self.db)
            results["members"] = await members_syncer.sync()
        except Exception as e:
            logger.warning(f"Members sync skipped: {e}")
            results["members"] = 0

        # Phase 2: Notes (also fetches companies on-demand, creates members/features/comments)
        logger.info("Syncing notes...")
        notes_syncer = NotesSyncer(self.db)
        results["notes"] = await notes_syncer.sync()

        logger.info(f"Sync complete: {results}")
        return results

    async def run_incremental_sync(self) -> dict:
        """Run incremental sync (same as full for now, but uses last_sync_time)."""
        return await self.run_full_sync()
