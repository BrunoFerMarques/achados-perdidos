import pytest
from psycopg.errors import CheckViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError

from models import User


def add_user(db, name: str, email: str) -> User:
    user = User(name=name, email=email, password_hash="hash")
    db.add(user)
    db.flush()
    return user


def test_user_is_created(db):
    user_id = add_user(db, "Maria Silva", "maria@example.com").id
    db.expunge_all()  # forget the loaded object, so the read below hits the database

    user = db.get(User, user_id)
    assert (user.name, user.email) == ("Maria Silva", "maria@example.com")


def test_email_is_unique_ignoring_case(db):
    add_user(db, "Maria Silva", "maria@example.com")

    with pytest.raises(IntegrityError) as error:
        add_user(db, "Maria Souza", "MARIA@example.com")
    assert isinstance(error.value.orig, UniqueViolation)


def test_invalid_email_is_rejected(db):
    with pytest.raises(IntegrityError) as error:
        add_user(db, "Maria Silva", "maria.example.com")
    assert isinstance(error.value.orig, CheckViolation)
