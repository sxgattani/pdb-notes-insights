from sqlalchemy.orm import Session

from app.services.sync.base import BaseSyncer
from app.models import Member
from app.integrations.productboard import ProductBoardClient, UsersAPI


class MembersSyncer(BaseSyncer[Member]):
    """Syncs members from ProductBoard users API."""

    entity_type = "members"

    async def sync(self) -> int:
        """Sync all members from ProductBoard."""
        self.start_sync()

        try:
            async with ProductBoardClient() as client:
                api = UsersAPI(client)
                pb_users = await api.list_users()

            count = 0
            for pb_user in pb_users:
                self._upsert_member(pb_user)
                count += 1

            self.db.commit()
            self.complete_sync(count)
            return count

        except Exception as e:
            self.fail_sync(str(e))
            raise

    def _upsert_member(self, pb_user: dict):
        """Insert or update a member."""
        pb_id = pb_user.get("id")
        email = pb_user.get("email")

        if not email:
            return

        # Try to find by email first (primary key for matching)
        member = self.db.query(Member).filter(Member.email == email).first()

        if not member:
            member = Member(email=email)
            self.db.add(member)

        member.pb_id = pb_id
        member.name = pb_user.get("name")


def get_or_create_member(db: Session, email: str, name: str = None, pb_id: str = None) -> Member:
    """Get or create a member by email. Used by notes syncer."""
    if not email:
        return None

    member = db.query(Member).filter(Member.email == email).first()

    if not member:
        member = Member(email=email, name=name, pb_id=pb_id)
        db.add(member)
        db.flush()  # Get the ID without committing
    else:
        # Update name/pb_id if provided and not set
        if name and not member.name:
            member.name = name
        if pb_id and not member.pb_id:
            member.pb_id = pb_id

    return member
