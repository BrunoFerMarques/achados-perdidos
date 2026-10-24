from fastapi import APIRouter

from dependencies import AuthServiceDep, CurrentUserDep
from schemas.auth import LoginRequest, TokenOut
from schemas.user import UserOut

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(payload: LoginRequest, auth: AuthServiceDep):
    return TokenOut(access_token=auth.login(payload.email, payload.password))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUserDep):
    return user
