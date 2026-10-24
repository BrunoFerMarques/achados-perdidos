from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    # no length rules here: a wrong password is a 401, not a validation error
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
