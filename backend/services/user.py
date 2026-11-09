from collections.abc import Sequence

from argon2 import PasswordHasher

from domain.errors import UserNotFound
from domain.permissions import can_list_users, can_manage_user, ensure
from models import User
from repositories.unit_of_work import UnitOfWork


class UserService:
    """Account use cases. `actor` is the logged-in user; the permission check comes first, so a
    user who may not see an account can't tell whether it exists."""

    def __init__(self, uow: UnitOfWork, password_hasher: PasswordHasher):
        self._uow = uow
        self._password_hasher = password_hasher

    def create(self, name: str, email: str, password: str) -> User:
        # public: registering is how a visitor becomes a user
        user = User(name=name, email=email, password_hash=self._password_hasher.hash(password))
        self._uow.users.add(user)
        self._uow.commit()
        return user

    def get(self, actor: User, user_id: int) -> User:
        ensure(can_manage_user(actor, user_id))
        return self._find(user_id)

    def list_page(self, actor: User, limit: int, offset: int) -> Sequence[User]:
        ensure(can_list_users(actor))
        return self._uow.users.list_page(limit, offset)

    def update(
        self,
        actor: User,
        user_id: int,
        name: str | None = None,
        email: str | None = None,
        password: str | None = None,
    ) -> User:
        ensure(can_manage_user(actor, user_id))
        user = self._find(user_id)
        # None keeps the current value
        if name is not None:
            user.name = name
        if email is not None:
            user.email = email
        if password is not None:
            user.password_hash = self._password_hasher.hash(password)
        self._uow.commit()
        return user

    def delete(self, actor: User, user_id: int) -> None:
        ensure(can_manage_user(actor, user_id))
        self._uow.users.delete(self._find(user_id))
        self._uow.commit()

    def _find(self, user_id: int) -> User:
        user = self._uow.users.get(user_id)
        if user is None:
            raise UserNotFound()
        return user
