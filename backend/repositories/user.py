from collections.abc import Sequence

from sqlalchemy import func, select

from models import User
from repositories.base import Repository


class UserRepository(Repository[User]):
    model = User

    def lock(self, user_id: int) -> User | None:
        """Trava a linha do usuário até o commit e recarrega. Com isso os pedidos do mesmo
        usuário rodam em fila, e os limites contados no banco não furam."""
        stmt = select(User).where(User.id == user_id).with_for_update()
        return self._session.scalars(stmt.execution_options(populate_existing=True)).one_or_none()

    def get_by_email(self, email: str) -> User | None:
        # mesma expressão do índice users_email_key, assim ignora maiúsculas e usa o índice
        stmt = select(User).where(func.lower(User.email) == func.lower(email))
        return self._session.scalars(stmt).one_or_none()

    def list_page(self, limit: int, offset: int) -> Sequence[User]:
        stmt = select(User).order_by(User.id).limit(limit).offset(offset)
        return self._session.scalars(stmt).all()
