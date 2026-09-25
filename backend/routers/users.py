from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field, StringConstraints

from db import get_conn
from services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    email: EmailStr
    # upper bound keeps argon2 hashing cheap for huge payloads
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, conn=Depends(get_conn)):
    try:
        return users_service.create_user(conn, payload.name, payload.email, payload.password)
    except users_service.EmailAlreadyRegisteredError:
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")
