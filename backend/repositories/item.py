from collections.abc import Sequence
from datetime import date

from sqlalchemy import select

from domain.items import DOCUMENTS_CATEGORY, PUBLIC_STATUSES
from models import Category, Item
from repositories.base import Repository


class ItemRepository(Repository[Item]):
    model = Item

    def get_for_update(self, item_id: int) -> Item | None:
        # locks the row until the commit: two attendants receiving the same item at once run one
        # after the other, and the second one sees the status the first one left (409)
        stmt = select(Item).where(Item.id == item_id).with_for_update()
        return self._session.scalars(stmt.execution_options(populate_existing=True)).one_or_none()

    def search_public(
        self,
        *,
        q: str | None,
        category_id: int | None,
        location_id: int | None,
        found_from: date | None,
        found_to: date | None,
    ) -> Sequence[Item]:
        # RN50: only what is at a collection point; the status never comes from the request
        stmt = select(Item).where(Item.status.in_(PUBLIC_STATUSES))
        if category_id is not None:
            stmt = stmt.where(Item.category_id == category_id)
        if location_id is not None:
            stmt = stmt.where(Item.location_id == location_id)
        if found_from is not None:
            stmt = stmt.where(Item.found_date >= found_from)
        if found_to is not None:
            stmt = stmt.where(Item.found_date <= found_to)
        if q:
            # RN52: the search skips documents, or finding one would confirm the name in it
            stmt = stmt.join(Item.category).where(
                Category.name != DOCUMENTS_CATEGORY,
                Item.description.ilike(f"%{q}%"),
            )
        # newest first; the id breaks ties between items found on the same day
        stmt = stmt.order_by(Item.found_date.desc(), Item.id.desc())
        return self._session.scalars(stmt).all()
