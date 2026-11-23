from typing import Annotated

from fastapi import APIRouter, Query

from dependencies import CurrentUserDep, UserServiceDep
from schemas.user import RoleUpdate, UserCreate, UserOut, UserUpdate

# toda rota pede login, menos o cadastro (sem token válido é 401 antes da rota rodar).
# O que cada usuário pode fazer fica no service (403)
router = APIRouter(prefix="/v1/users", tags=["users"])


@router.post("", status_code=201, response_model=UserOut)
def create_user(payload: UserCreate, users: UserServiceDep):
    return users.create(payload.name, payload.email, payload.password)


@router.get("", response_model=list[UserOut])
def list_users(
    current_user: CurrentUserDep,
    users: UserServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return users.list_page(current_user, limit, offset)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, current_user: CurrentUserDep, users: UserServiceDep):
    return users.get(current_user, user_id)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int, payload: UserUpdate, current_user: CurrentUserDep, users: UserServiceDep
):
    return users.update(current_user, user_id, payload.name, payload.email, payload.password)


# rota separada do UserUpdate porque tem regra própria (só admin, e nunca o próprio papel)
@router.patch("/{user_id}/role", response_model=UserOut)
def change_user_role(
    user_id: int, payload: RoleUpdate, current_user: CurrentUserDep, users: UserServiceDep
):
    return users.change_role(current_user, user_id, payload.role)


# desbloqueio é uma ação, não um campo; o bloqueio em si sai das rejeições
@router.post("/{user_id}/unblock", status_code=204)
def unblock_user(user_id: int, current_user: CurrentUserDep, users: UserServiceDep):
    users.unblock(current_user, user_id)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, current_user: CurrentUserDep, users: UserServiceDep):
    users.delete(current_user, user_id)
