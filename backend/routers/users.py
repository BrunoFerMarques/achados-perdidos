from typing import Annotated

from fastapi import APIRouter, Query

from dependencies import UserServiceDep
from schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.post("", status_code=201, response_model=UserOut)
def create_user(payload: UserCreate, users: UserServiceDep):
    return users.create(payload.name, payload.email, payload.password)


@router.get("", response_model=list[UserOut])
def list_users(
    users: UserServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return users.list_page(limit, offset)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, users: UserServiceDep):
    return users.get(user_id)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, users: UserServiceDep):
    return users.update(user_id, payload.name, payload.email, payload.password)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, users: UserServiceDep):
    users.delete(user_id)
