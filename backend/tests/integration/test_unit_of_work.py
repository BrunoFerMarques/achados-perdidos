import pytest
from sqlalchemy.exc import IntegrityError

from domain.errors import EmailAlreadyExists
from models import User
from repositories.unit_of_work import UnitOfWork


def new_user(name: str = "Maria Silva", email: str = "maria@example.com") -> User:
    return User(name=name, email=email, password_hash="hash")


def test_commit_turns_a_known_constraint_into_a_domain_error(db):
    uow = UnitOfWork(db)
    uow.users.add(new_user())
    uow.commit()

    uow.users.add(new_user(email="MARIA@example.com"))
    with pytest.raises(EmailAlreadyExists):
        uow.commit()


def test_commit_keeps_unexpected_integrity_errors(db):
    # a blank name is blocked by the API, so reaching the database means a bug
    uow = UnitOfWork(db)
    uow.users.add(new_user(name="   "))

    with pytest.raises(IntegrityError):
        uow.commit()


def test_session_is_usable_after_a_failed_commit(db):
    uow = UnitOfWork(db)
    uow.users.add(new_user())
    uow.commit()
    uow.users.add(new_user(email="MARIA@example.com"))
    with pytest.raises(EmailAlreadyExists):
        uow.commit()

    uow.users.add(new_user(email="joao@example.com"))
    uow.commit()

    assert [user.email for user in uow.users.list_page(10, 0)] == [
        "maria@example.com",
        "joao@example.com",
    ]
