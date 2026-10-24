from fastapi import APIRouter

from dependencies import AuthServiceDep
from schemas.auth import LoginRequest, TokenOut

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(payload: LoginRequest, auth: AuthServiceDep):
    return TokenOut(access_token=auth.login(payload.email, payload.password))
