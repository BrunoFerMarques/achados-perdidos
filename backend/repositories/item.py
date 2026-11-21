from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from domain.items import ItemStatus
from models import Item
from repositories.base import Repository


class ItemRepository(Repository[Item]):
    model = Item

    def get_for_update(self, item_id: int) -> Item | None:
        # locks the row until the commit: two attendants receiving the same item at once run one
        # after the other, and the second one sees the status the first one left (409)
        stmt = select(Item).where(Item.id == item_id).with_for_update()
        return self._session.scalars(stmt.execution_options(populate_existing=True)).one_or_none()

    def list_in_transfer(self, point_ids: set[int] | None) -> Sequence[Item]:
        """Items on their way, in registration order; `point_ids` keeps the ones leaving or heading
        to those points (RN41), and None means every point. The questions come along for ItemOut."""
        stmt = (
            select(Item)
            .where(Item.status == ItemStatus.IN_TRANSFER)
            .options(selectinload(Item.questions))
            .order_by(Item.id)
        )
        if point_ids is not None:
            stmt = stmt.where(
                or_(Item.collection_point_id.in_(point_ids), Item.transfer_to_id.in_(point_ids))
            )
        return self._session.scalars(stmt).all()
