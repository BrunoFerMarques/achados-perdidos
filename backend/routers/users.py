from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from db import get_conn
from schemas.user import UserCreate, UserOut
from services import user as user_service

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.post("", status_code=201, response_model=UserOut)
def create_user(payload: UserCreate, conn: Annotated[psycopg.Connection, Depends(get_conn)]):
    try:
        return user_service.create_user(conn, payload.name, payload.email, payload.password)
    except user_service.EmailAlreadyExists:
        raise HTTPException(status_code=409, detail="E-mail já cadastrado") from None
