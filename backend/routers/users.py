from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from db import SessionDep
from schemas.user import UserCreate, UserOut, UserUpdate
from services import user as user_service

router = APIRouter(prefix="/v1/users", tags=["users"])


def _user_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Usuário não encontrado")


@router.post("", status_code=201, response_model=UserOut)
def create_user(payload: UserCreate, session: SessionDep):
    try:
        return user_service.create_user(session, payload.name, payload.email, payload.password)
    except user_service.EmailAlreadyExists:
        raise HTTPException(status_code=409, detail="E-mail já cadastrado") from None


@router.get("", response_model=list[UserOut])
def list_users(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return user_service.list_users(session, limit, offset)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, session: SessionDep):
    user = user_service.get_user(session, user_id)
    if user is None:
        raise _user_not_found()
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, session: SessionDep):
    try:
        user = user_service.update_user(
            session, user_id, payload.name, payload.email, payload.password
        )
    except user_service.EmailAlreadyExists:
        raise HTTPException(status_code=409, detail="E-mail já cadastrado") from None
    if user is None:
        raise _user_not_found()
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, session: SessionDep):
    if not user_service.delete_user(session, user_id):
        raise _user_not_found()
