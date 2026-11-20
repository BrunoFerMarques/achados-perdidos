from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from domain.items import MAX_QUESTIONS, MIN_QUESTIONS

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class QuestionIn(BaseModel):
    question: Text
    answer: Text


class ItemCreate(BaseModel):
    # no status and no finder_id: the database and the token fill them in
    category_id: int
    location_id: int
    color_id: int
    collection_point_id: int
    description: Text
    found_date: date
    # RN20: from 2 to 5 questions, or 422 before the service runs
    questions: Annotated[
        list[QuestionIn], Field(min_length=MIN_QUESTIONS, max_length=MAX_QUESTIONS)
    ]


class ReceiveIn(BaseModel):
    # the counter where the object is handed in (RN02), not the point the finder chose
    collection_point_id: int


class QuestionOut(BaseModel):
    """No answer field: the expected answer never leaves the API (RN23)."""

    model_config = ConfigDict(from_attributes=True)

    position: int
    question: str


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    location_id: int
    color_id: int
    collection_point_id: int
    finder_id: int | None
    description: str
    found_date: date
    status: str
    created_at: datetime
    questions: list[QuestionOut]
