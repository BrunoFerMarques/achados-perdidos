from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    # sem regra de tamanho: senha errada é 401, não erro de validação
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
