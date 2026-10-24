from collections.abc import Sequence

from sqlalchemy import func, select

from models import User
from repositories.base import Repository


class UserRepository(Repository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        # same expression as the users_email_key index, so the lookup ignores case and uses it
        stmt = select(User).where(func.lower(User.email) == func.lower(email))
        return self._session.scalars(stmt).one_or_none()

    def list_page(self, limit: int, offset: int) -> Sequence[User]:
        stmt = select(User).order_by(User.id).limit(limit).offset(offset)
        return self._session.scalars(stmt).all()
