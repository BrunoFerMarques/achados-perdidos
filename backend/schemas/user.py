from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]


class UserCreate(BaseModel):
    name: Name
    email: EmailStr
    password: Password


class UserUpdate(BaseModel):
    # only the fields sent are changed; None means "keep the current value"
    name: Name | None = None
    email: EmailStr | None = None
    password: Password | None = None

    @model_validator(mode="after")
    def check_fields(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para atualizar")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Os campos não podem ser nulos")
        return self


class UserOut(BaseModel):
    # built from the User model returned by the services
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    created_at: datetime
