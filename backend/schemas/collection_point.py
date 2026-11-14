from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

PointName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class CollectionPointCreate(BaseModel):
    name: PointName


class CollectionPointOut(BaseModel):
    # built from the CollectionPoint model returned by the services
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class AttendantLink(BaseModel):
    user_id: int
