from datetime import datetime, timezone
from typing import Optional
import logging

from sqlalchemy.orm import Session

from app.services.sync.base import BaseSyncer
from app.services.sync.members_syncer import get_or_create_member
from app.models import Note, Member, Company, Feature, NoteFeature, NoteComment
from app.integrations.productboard import ProductBoardClient, NotesAPI, CompaniesAPI

logger = logging.getLogger(__name__)


class NotesSyncer(BaseSyncer[Note]):
    """Syncs notes from ProductBoard."""

    entity_type = "notes"

    def __init__(self, db):
        super().__init__(db)
        self._companies_api: Optional[CompaniesAPI] = None
        self._company_cache: dict[str, int] = {}  # pb_id -> id

    async def sync(self) -> int:
        """Sync notes from ProductBoard (incremental)."""
        self.start_sync()
        last_sync = self.get_last_sync_time()

        # Build cache of existing companies
        self._company_cache = {
            c.pb_id: c.id for c in self.db.query(Company.pb_id, Company.id).all()
        }

        try:
            async with ProductBoardClient() as client:
                notes_api = NotesAPI(client)
                self._companies_api = CompaniesAPI(client)

                pb_notes = await notes_api.list_notes(updated_after=last_sync)

                count = 0
                processed_note_ids = []

                for pb_note in pb_notes:
                    note = await self._upsert_note(pb_note)
                    count += 1

                    # Track processed notes for enrichment
                    if note and note.state == "processed":
                        processed_note_ids.append(note.pb_id)

                self.db.commit()

                # Enrich processed notes with full details (comments)
                if processed_note_ids:
                    logger.info(f"Enriching {len(processed_note_ids)} processed notes...")
                    await self._enrich_notes(notes_api, processed_note_ids)
                    self.db.commit()

            self.complete_sync(count)
            return count

        except Exception as e:
            self.fail_sync(str(e))
            raise
        finally:
            self._companies_api = None

    async def _enrich_notes(self, api: NotesAPI, note_pb_ids: list[str]):
        """Fetch full details for notes to get comments."""
        for pb_id in note_pb_ids:
            try:
                pb_note = await api.get_note(pb_id)
                if pb_note:
                    self._enrich_note(pb_note)
            except Exception as e:
                logger.warning(f"Failed to enrich note {pb_id}: {e}")

    def _enrich_note(self, pb_note: dict):
        """Update a note with enriched data (comments)."""
        pb_id = pb_note.get("id")
        note = self.db.query(Note).filter(Note.pb_id == pb_id).first()

        if not note:
            return

        # Update enrichment timestamp
        note.enriched_at = datetime.now(timezone.utc)

        # Update external display URL
        note.external_display_url = pb_note.get("externalDisplayUrl")

        # Sync comments (most recent 5)
        self._sync_note_comments(note, pb_note.get("comments", []))

    async def _get_or_fetch_company(self, company_pb_id: str) -> Optional[int]:
        """Get company ID from cache or fetch from API."""
        # Check cache first
        if company_pb_id in self._company_cache:
            return self._company_cache[company_pb_id]

        # Fetch from API
        if self._companies_api:
            try:
                pb_company = await self._companies_api.get_company(company_pb_id)
                if pb_company:
                    company = self._upsert_company(pb_company)
                    self._company_cache[company_pb_id] = company.id
                    return company.id
            except Exception as e:
                logger.warning(f"Failed to fetch company {company_pb_id}: {e}")

        return None

    def _upsert_company(self, pb_company: dict) -> Company:
        """Insert or update a company."""
        pb_id = pb_company.get("id")

        company = self.db.query(Company).filter(Company.pb_id == pb_id).first()

        if not company:
            company = Company(pb_id=pb_id)
            self.db.add(company)

        company.name = pb_company.get("name")
        company.domain = pb_company.get("domain")

        # Custom fields if available
        custom_fields = pb_company.get("customFields", {})
        if custom_fields:
            company.customer_id = custom_fields.get("customer_id")
            company.account_sales_theatre = custom_fields.get("account_sales_theatre")
            company.cse = custom_fields.get("cse")
            company.account_type = custom_fields.get("account_type")
            # Parse ARR if present
            arr_value = custom_fields.get("arr")
            if arr_value:
                try:
                    company.arr = float(arr_value)
                except (ValueError, TypeError):
                    pass

        self.db.flush()
        return company

    async def _upsert_note(self, pb_note: dict) -> Optional[Note]:
        """Insert or update a note."""
        pb_id = pb_note.get("id")

        note = self.db.query(Note).filter(Note.pb_id == pb_id).first()
        is_new = note is None

        if is_new:
            note = Note(pb_id=pb_id)
            self.db.add(note)

        # Basic fields
        note.title = pb_note.get("title")
        note.content = pb_note.get("content")
        note.state = pb_note.get("state", "unprocessed")
        note.display_url = pb_note.get("displayUrl")
        note.external_display_url = pb_note.get("externalDisplayUrl")
        note.tags = pb_note.get("tags", [])

        # Followers count
        followers = pb_note.get("followers", [])
        note.followers_count = len(followers)

        # Handle source
        source_data = pb_note.get("source")
        if isinstance(source_data, dict):
            note.source_origin = source_data.get("origin")
        else:
            note.source_origin = source_data

        # Parse dates
        if pb_note.get("createdAt"):
            note.created_at = datetime.fromisoformat(
                pb_note["createdAt"].replace("Z", "+00:00")
            )
        if pb_note.get("updatedAt"):
            note.updated_at = datetime.fromisoformat(
                pb_note["updatedAt"].replace("Z", "+00:00")
            )

        # Handle state change for processed_at
        if note.state == "processed" and not note.processed_at:
            note.processed_at = datetime.now(timezone.utc)

        # Resolve owner (PM)
        owner_data = pb_note.get("owner")
        if owner_data and isinstance(owner_data, dict):
            owner_email = owner_data.get("email")
            owner_name = owner_data.get("name")
            if owner_email:
                owner = get_or_create_member(self.db, owner_email, owner_name)
                if owner:
                    note.owner_id = owner.id

        # Resolve created_by
        created_by_data = pb_note.get("createdBy")
        if created_by_data and isinstance(created_by_data, dict):
            created_by_email = created_by_data.get("email")
            created_by_name = created_by_data.get("name")
            created_by_pb_id = created_by_data.get("id")
            if created_by_email:
                created_by = get_or_create_member(
                    self.db, created_by_email, created_by_name, created_by_pb_id
                )
                if created_by:
                    note.created_by_id = created_by.id

        # Resolve company (fetch if not exists)
        company_data = pb_note.get("company")
        if company_data and isinstance(company_data, dict):
            company_pb_id = company_data.get("id")
            if company_pb_id:
                note.company_pb_id = company_pb_id
                company_id = await self._get_or_fetch_company(company_pb_id)
                if company_id:
                    note.company_id = company_id

        # Flush to get note.id for relationships
        self.db.flush()

        # Handle features
        self._sync_note_features(note, pb_note.get("features", []))

        return note

    def _sync_note_features(self, note: Note, features_data: list):
        """Sync features linked to a note."""
        if not features_data:
            return

        # Clear existing links for this note
        self.db.query(NoteFeature).filter(NoteFeature.note_id == note.id).delete()

        for feature_data in features_data:
            feature_pb_id = feature_data.get("id")
            if not feature_pb_id:
                continue

            # Get or create feature
            feature = self.db.query(Feature).filter(
                Feature.pb_id == feature_pb_id
            ).first()

            if not feature:
                feature = Feature(pb_id=feature_pb_id)
                self.db.add(feature)
                self.db.flush()

            # Create link
            note_feature = NoteFeature(
                note_id=note.id,
                feature_id=feature.id,
                importance=feature_data.get("importance")
            )
            self.db.add(note_feature)

    def _sync_note_comments(self, note: Note, comments_data: list):
        """Sync most recent 5 comments for a note."""
        if not comments_data:
            return

        # Sort by timestamp descending and take top 5
        sorted_comments = sorted(
            comments_data,
            key=lambda c: c.get("timestamp", ""),
            reverse=True
        )[:5]

        # Delete existing comments for this note and recreate
        self.db.query(NoteComment).filter(NoteComment.note_id == note.id).delete()

        for comment_data in sorted_comments:
            comment_pb_id = comment_data.get("id")
            if not comment_pb_id:
                continue

            # Get or create member for commenter
            comment_email = comment_data.get("email")
            member = None
            if comment_email:
                member = get_or_create_member(self.db, comment_email)

            # Parse timestamp
            timestamp = None
            if comment_data.get("timestamp"):
                timestamp = datetime.fromisoformat(
                    comment_data["timestamp"].replace("Z", "+00:00")
                )

            comment = NoteComment(
                pb_id=comment_pb_id,
                note_id=note.id,
                member_id=member.id if member else None,
                content=comment_data.get("content"),
                timestamp=timestamp
            )
            self.db.add(comment)
