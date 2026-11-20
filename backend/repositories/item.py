from sqlalchemy import select

from models import Item
from repositories.base import Repository


class ItemRepository(Repository[Item]):
    model = Item

    def get_for_update(self, item_id: int) -> Item | None:
        # locks the row until the commit: two attendants receiving the same item at once run one
        # after the other, and the second one sees the status the first one left (409)
        stmt = select(Item).where(Item.id == item_id).with_for_update()
        return self._session.scalars(stmt.execution_options(populate_existing=True)).one_or_none()
