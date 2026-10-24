from collections.abc import Sequence

from argon2 import PasswordHasher

from domain.errors import UserNotFound
from models import User
from repositories.unit_of_work import UnitOfWork


class UserService:
    def __init__(self, uow: UnitOfWork, password_hasher: PasswordHasher):
        self._uow = uow
        self._password_hasher = password_hasher

    def create(self, name: str, email: str, password: str) -> User:
        user = User(name=name, email=email, password_hash=self._password_hasher.hash(password))
        self._uow.users.add(user)
        self._uow.commit()
        return user

    def get(self, user_id: int) -> User:
        user = self._uow.users.get(user_id)
        if user is None:
            raise UserNotFound()
        return user

    def list_page(self, limit: int, offset: int) -> Sequence[User]:
        return self._uow.users.list_page(limit, offset)

    def update(
        self,
        user_id: int,
        name: str | None = None,
        email: str | None = None,
        password: str | None = None,
    ) -> User:
        user = self.get(user_id)
        # None keeps the current value
        if name is not None:
            user.name = name
        if email is not None:
            user.email = email
        if password is not None:
            user.password_hash = self._password_hasher.hash(password)
        self._uow.commit()
        return user

    def delete(self, user_id: int) -> None:
        self._uow.users.delete(self.get(user_id))
        self._uow.commit()
