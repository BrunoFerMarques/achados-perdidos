from collections.abc import Sequence
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from domain.items import DOCUMENTS_CATEGORY, PUBLIC_STATUSES, ItemStatus
from models import Category, Item
from repositories.base import Repository


class ItemRepository(Repository[Item]):
    model = Item

    def get_for_update(self, item_id: int) -> Item | None:
        # locks the row until the commit: two attendants receiving the same item at once run one
        # after the other, and the second one sees the status the first one left (409)
        stmt = select(Item).where(Item.id == item_id).with_for_update()
        return self._session.scalars(stmt.execution_options(populate_existing=True)).one_or_none()

    def list_registered(self) -> Sequence[Item]:
        """Items no counter has received yet, oldest first, from every point: the finder may hand
        an item in anywhere (RN02). The questions come along for ItemOut."""
        stmt = (
            select(Item)
            .where(Item.status == ItemStatus.REGISTERED)
            .options(selectinload(Item.questions))
            .order_by(Item.id)
        )
        return self._session.scalars(stmt).all()

    def list_in_transfer(self, point_ids: set[int] | None) -> Sequence[Item]:
        """Itens em transferência, por ordem de registro. `point_ids` filtra os que saem ou
        chegam nesses pontos (None = todos). Traz as perguntas junto por causa do ItemOut."""
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
