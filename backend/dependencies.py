"""Composition root: the one place that decides which object each route receives."""

from typing import Annotated

from argon2 import PasswordHasher
from fastapi import Depends

from db import SessionDep
from repositories.unit_of_work import UnitOfWork
from services.user import UserService

_password_hasher = PasswordHasher()


def get_unit_of_work(session: SessionDep) -> UnitOfWork:
    return UnitOfWork(session)


UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_user_service(uow: UnitOfWorkDep) -> UserService:
    return UserService(uow, _password_hasher)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
