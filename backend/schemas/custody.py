from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CustodyRecordOut(BaseModel):
    """One line of an item's custody history, for the staff (RN42, RN53)."""

    model_config = ConfigDict(from_attributes=True)

    event: str
    collection_point_id: int
    actor_id: int | None
    # RN42: who was responsible; None when the account was deleted
    actor_name: str | None
    at: datetime
