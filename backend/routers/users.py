from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from db import get_conn
from schemas.user import UserCreate, UserOut
from services import user as user_service

router = APIRouter(prefix="/v1/users", tags=["users"])

Conn = Annotated[psycopg.Connection, Depends(get_conn)]


def _user_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Usuário não encontrado")


@router.post("", status_code=201, response_model=UserOut)
def create_user(payload: UserCreate, conn: Conn):
    try:
        return user_service.create_user(conn, payload.name, payload.email, payload.password)
    except user_service.EmailAlreadyExists:
        raise HTTPException(status_code=409, detail="E-mail já cadastrado") from None


@router.get("", response_model=list[UserOut])
def list_users(
    conn: Conn,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return user_service.list_users(conn, limit, offset)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, conn: Conn):
    user = user_service.get_user(conn, user_id)
    if user is None:
        raise _user_not_found()
    return user
