from collections.abc import Sequence

from sqlalchemy import select

from models import User
from repositories.base import Repository


class UserRepository(Repository[User]):
    model = User

    def list_page(self, limit: int, offset: int) -> Sequence[User]:
        stmt = select(User).order_by(User.id).limit(limit).offset(offset)
        return self._session.scalars(stmt).all()
