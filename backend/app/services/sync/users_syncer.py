from sqlalchemy.orm import Session

from app.services.sync.base import BaseSyncer
from app.models import User
from app.integrations.productboard import ProductBoardClient, UsersAPI


class UsersSyncer(BaseSyncer[User]):
    """Syncs users from ProductBoard."""

    entity_type = "users"

    async def sync(self) -> int:
        """Sync all users from ProductBoard."""
        self.start_sync()

        try:
            async with ProductBoardClient() as client:
                api = UsersAPI(client)
                pb_users = await api.list_users()

            count = 0
            for pb_user in pb_users:
                self._upsert_user(pb_user)
                count += 1

            self.db.commit()
            self.complete_sync(count)
            return count

        except Exception as e:
            self.fail_sync(str(e))
            raise

    def _upsert_user(self, pb_user: dict):
        """Insert or update a user."""
        pb_id = pb_user.get("id")

        user = self.db.query(User).filter(User.pb_id == pb_id).first()

        if not user:
            user = User(pb_id=pb_id)
            self.db.add(user)

        user.name = pb_user.get("name")
        user.email = pb_user.get("email")
        user.role = pb_user.get("role")
