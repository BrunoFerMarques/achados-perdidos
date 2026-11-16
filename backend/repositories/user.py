from collections.abc import Sequence

from sqlalchemy import func, select

from models import User
from repositories.base import Repository


class UserRepository(Repository[User]):
    model = User

    def lock(self, user_id: int) -> User | None:
        """Locks the user's row until the commit and reloads it. Whatever a user does under the
        lock runs one request at a time, so limits counted from the database can't be raced."""
        stmt = select(User).where(User.id == user_id).with_for_update()
        return self._session.scalars(stmt.execution_options(populate_existing=True)).one_or_none()

    def get_by_email(self, email: str) -> User | None:
        # same expression as the users_email_key index, so the lookup ignores case and uses it
        stmt = select(User).where(func.lower(User.email) == func.lower(email))
        return self._session.scalars(stmt).one_or_none()

    def list_page(self, limit: int, offset: int) -> Sequence[User]:
        stmt = select(User).order_by(User.id).limit(limit).offset(offset)
        return self._session.scalars(stmt).all()
