"""Composition root: the one place that decides which object each route receives."""

import os
from datetime import timedelta
from typing import Annotated

from argon2 import PasswordHasher
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db import SessionDep
from domain.errors import NotAuthenticated
from models import User
from repositories.unit_of_work import UnitOfWork
from services.auth import AuthService
from services.token import TokenService
from services.user import UserService

TOKEN_TTL = timedelta(hours=1)

_password_hasher = PasswordHasher()
# auto_error=False: a missing token raises NotAuthenticated, so every auth failure is the same 401
_bearer = HTTPBearer(auto_error=False)


def get_unit_of_work(session: SessionDep) -> UnitOfWork:
    return UnitOfWork(session)


UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_user_service(uow: UnitOfWorkDep) -> UserService:
    return UserService(uow, _password_hasher)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_token_service() -> TokenService:
    # read on every call, like DATABASE_URL: the .env is loaded after this module is imported
    return TokenService(os.environ["JWT_SECRET"], TOKEN_TTL)


TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]


def get_auth_service(uow: UnitOfWorkDep, tokens: TokenServiceDep) -> AuthService:
    return AuthService(uow, _password_hasher, tokens)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    auth: AuthServiceDep,
) -> User:
    if credentials is None:
        raise NotAuthenticated()
    return auth.authenticate(credentials.credentials)


# a route that takes this parameter only runs for a logged-in user
CurrentUserDep = Annotated[User, Depends(get_current_user)]
