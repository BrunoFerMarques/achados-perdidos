from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class LostReportCreate(BaseModel):
    category_id: int
    location_id: int
    color_id: int
    description: Description
    lost_date: date


class LostReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    category_id: int
    location_id: int
    color_id: int
    description: str
    lost_date: date
    status: str
    created_at: datetime
