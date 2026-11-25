"""Composition root: aqui se decide o que cada rota recebe."""

import os
from datetime import timedelta
from typing import Annotated

from argon2 import PasswordHasher
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db import SessionDep
from domain.clock import Clock, SystemClock
from domain.errors import NotAuthenticated
from models import User
from repositories.unit_of_work import UnitOfWork
from services.auth import AuthService
from services.category import CategoryService
from services.claim import ClaimService
from services.collection_point import CollectionPointService
from services.color import ColorService
from services.item import ItemService
from services.location import LocationService
from services.lost_report import LostReportService
from services.match_handler import MatchHandler
from services.notification import NotificationService
from services.token import TokenService
from services.user import UserService

TOKEN_TTL = timedelta(hours=1)

_password_hasher = PasswordHasher()
_system_clock = SystemClock()
# auto_error=False pra qualquer falha de token virar o mesmo 401 (NotAuthenticated)
_bearer = HTTPBearer(auto_error=False)


def get_clock() -> Clock:
    # nos testes isso é trocado por um relógio falso (dependency_overrides)
    return _system_clock


ClockDep = Annotated[Clock, Depends(get_clock)]


def get_unit_of_work(session: SessionDep) -> UnitOfWork:
    return UnitOfWork(session)


UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_user_service(uow: UnitOfWorkDep, clock: ClockDep) -> UserService:
    return UserService(uow, _password_hasher, clock)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_category_service(uow: UnitOfWorkDep) -> CategoryService:
    return CategoryService(uow)


CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]


def get_location_service(uow: UnitOfWorkDep) -> LocationService:
    return LocationService(uow)


LocationServiceDep = Annotated[LocationService, Depends(get_location_service)]


def get_color_service(uow: UnitOfWorkDep) -> ColorService:
    return ColorService(uow)


ColorServiceDep = Annotated[ColorService, Depends(get_color_service)]


def get_collection_point_service(uow: UnitOfWorkDep) -> CollectionPointService:
    return CollectionPointService(uow)


CollectionPointServiceDep = Annotated[CollectionPointService, Depends(get_collection_point_service)]


def get_item_service(uow: UnitOfWorkDep, clock: ClockDep) -> ItemService:
    handler = MatchHandler(uow)
    return ItemService(uow, clock, handler.on_item_available)


ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]


def get_claim_service(uow: UnitOfWorkDep, clock: ClockDep) -> ClaimService:
    return ClaimService(uow, clock)


ClaimServiceDep = Annotated[ClaimService, Depends(get_claim_service)]


def get_token_service() -> TokenService:
    # lido a cada chamada porque o .env só é carregado depois deste import
    return TokenService(os.environ["JWT_SECRET"], TOKEN_TTL)


TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]


def get_auth_service(uow: UnitOfWorkDep, tokens: TokenServiceDep) -> AuthService:
    return AuthService(uow, _password_hasher, tokens)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_lost_report_service(uow: UnitOfWorkDep) -> LostReportService:
    handler = MatchHandler(uow)
    return LostReportService(uow, handler.on_report_created)


LostReportServiceDep = Annotated[LostReportService, Depends(get_lost_report_service)]


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    auth: AuthServiceDep,
) -> User:
    if credentials is None:
        raise NotAuthenticated()
    return auth.authenticate(credentials.credentials)


# rota com esse parâmetro só roda com usuário logado
CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_notification_service(uow: UnitOfWorkDep, clock: ClockDep) -> NotificationService:
    return NotificationService(uow, clock)


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]
