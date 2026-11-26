from datetime import datetime

from pydantic import BaseModel, ConfigDict

from schemas.item import ItemPublicOut


class NotificationOut(BaseModel):
    # RN32: expose only the item's public information.
    model_config = ConfigDict(from_attributes=True)

    id: int
    lost_report_id: int
    item_id: int
    created_at: datetime
    read_at: datetime | None
    item_available: bool
    item: ItemPublicOut
