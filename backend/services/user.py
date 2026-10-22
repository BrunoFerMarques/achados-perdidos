from argon2 import PasswordHasher
from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import User

_hasher = PasswordHasher()


class EmailAlreadyExists(Exception):
    pass


def _commit(session: Session, email: str | None) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        # the e-mail index is the only unique constraint on users
        if isinstance(error.orig, UniqueViolation):
            raise EmailAlreadyExists(email) from None
        raise


def create_user(session: Session, name: str, email: str, password: str) -> User:
    user = User(name=name, email=email, password_hash=_hasher.hash(password))
    session.add(user)
    _commit(session, email)
    return user


def get_user(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def list_users(session: Session, limit: int, offset: int) -> list[User]:
    stmt = select(User).order_by(User.id).limit(limit).offset(offset)
    return list(session.scalars(stmt))


def update_user(
    session: Session,
    user_id: int,
    name: str | None = None,
    email: str | None = None,
    password: str | None = None,
) -> User | None:
    user = session.get(User, user_id)
    if user is None:
        return None
    # None keeps the current value
    if name is not None:
        user.name = name
    if email is not None:
        user.email = email
    if password is not None:
        user.password_hash = _hasher.hash(password)
    _commit(session, email)
    return user


def delete_user(session: Session, user_id: int) -> bool:
    user = session.get(User, user_id)
    if user is None:
        return False
    session.delete(user)
    session.commit()
    return True
