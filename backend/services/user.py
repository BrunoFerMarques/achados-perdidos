from collections.abc import Sequence

from argon2 import PasswordHasher

from domain.clock import Clock
from domain.errors import UserNotFound
from domain.permissions import (
    can_change_role,
    can_list_users,
    can_manage_user,
    can_unblock_user,
    ensure,
)
from domain.roles import Role
from models import User
from repositories.unit_of_work import UnitOfWork


class UserService:
    """Casos de uso das contas. `actor` é quem está logado, e a permissão é checada antes de
    buscar, então quem não pode ver uma conta nem descobre se ela existe."""

    def __init__(self, uow: UnitOfWork, password_hasher: PasswordHasher, clock: Clock):
        self._uow = uow
        self._password_hasher = password_hasher
        self._clock = clock

    def create(self, name: str, email: str, password: str) -> User:
        # público: é assim que um visitante vira usuário
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
        # None mantém o valor atual
        if name is not None:
            user.name = name
        if email is not None:
            user.email = email
        if password is not None:
            user.password_hash = self._password_hasher.hash(password)
        self._uow.commit()
        return user

    def change_role(self, actor: User, user_id: int, role: Role) -> User:
        ensure(can_change_role(actor, user_id))
        user = self._find(user_id)
        user.role = role
        self._uow.commit()
        return user

    def unblock(self, actor: User, user_id: int) -> None:
        ensure(can_unblock_user(actor))
        user = self._find(user_id)
        # falhas antes deste momento param de contar. Se o usuário nem estava bloqueado, isso
        # também zera as falhas que ainda não tinham dado bloqueio (é decisão do admin). Usa o
        # mesmo relógio que o domain/blocking.py recebe como `now`
        user.unblocked_at = self._clock.now()
        self._uow.commit()

    def promote_to_admin(self, email: str) -> User:
        """Só usado pelo make_admin.py pra criar o primeiro admin. Não tem permissão pra checar,
        quem roda o script já tem acesso direto ao banco."""
        user = self._uow.users.get_by_email(email)
        if user is None:
            raise UserNotFound()
        user.role = Role.ADMIN
        self._uow.commit()
        return user

    def delete(self, actor: User, user_id: int) -> None:
        ensure(can_manage_user(actor, user_id))
        user = self._find(user_id)
        # as reivindicações somem com a conta (CASCADE), mas antes a aprovada devolve o item,
        # senão ele ficaria reservado pra ninguém
        for claim in self._uow.claims.lock_active_by_claimant(user_id):
            claim.cancel(by=actor.id, at=self._clock.now())
        # the liberacao lines go in before the account leaves: SQLAlchemy would delete the user
        # first, and a line pointing at a user that no longer exists breaks the foreign key
        self._uow.flush()
        self._uow.users.delete(user)
        self._uow.commit()

    def _find(self, user_id: int) -> User:
        user = self._uow.users.get(user_id)
        if user is None:
            raise UserNotFound()
        return user
