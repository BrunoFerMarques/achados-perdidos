from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from domain.errors import InvalidCredentials, InvalidToken
from models import User
from repositories.unit_of_work import UnitOfWork
from services.token import TokenService


class AuthService:
    def __init__(self, uow: UnitOfWork, password_hasher: PasswordHasher, tokens: TokenService):
        self._uow = uow
        self._password_hasher = password_hasher
        self._tokens = tokens

    def login(self, email: str, password: str) -> str:
        user = self._uow.users.get_by_email(email)
        # one message for both cases, so the response doesn't say which part was wrong
        if user is None or not self._password_matches(user, password):
            raise InvalidCredentials()
        return self._tokens.issue(user.id)

    def authenticate(self, token: str) -> User:
        user = self._uow.users.get(self._tokens.user_id(token))
        # the token is still signed after the account is deleted
        if user is None:
            raise InvalidToken()
        return user

    def _password_matches(self, user: User, password: str) -> bool:
        try:
            return self._password_hasher.verify(user.password_hash, password)
        except VerificationError:
            return False
