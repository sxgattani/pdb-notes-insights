import logging
from sqlalchemy.orm import Session

from app.services.sync.users_syncer import UsersSyncer
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
        1. Users & Teams (no dependencies)
        2. Companies (no dependencies)
        3. Customers (depends on companies)
        4. Components (no dependencies)
        5. Features (depends on components, users, teams)
        6. Notes (depends on customers, users, teams)
        7. Relationships (depends on notes, features)
        """
        results = {}

        # Phase 1: Independent entities
        logger.info("Syncing users...")
        users_syncer = UsersSyncer(self.db)
        results["users"] = await users_syncer.sync()

        # Phase 2: Notes (simplified for now - add more syncers later)
        logger.info("Syncing notes...")
        notes_syncer = NotesSyncer(self.db)
        results["notes"] = await notes_syncer.sync()

        logger.info(f"Sync complete: {results}")
        return results

    async def run_incremental_sync(self) -> dict:
        """Run incremental sync (same as full for now, but uses last_sync_time)."""
        return await self.run_full_sync()
