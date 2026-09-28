from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, StringConstraints


class UserCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime
