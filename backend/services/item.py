from collections.abc import Sequence
from datetime import date

from domain.clock import Clock
from domain.custody import CustodyEvent
from domain.errors import (
    CategoryNotFound,
    CollectionPointNotFound,
    ColorNotFound,
    ItemNotFound,
    LocationNotFound,
)
from domain.permissions import can_operate_item, can_view_custody, ensure
from models import CustodyRecord, Item, ItemQuestion, User
from repositories.unit_of_work import UnitOfWork


class ItemService:
    """Found items (scope §4.1). The finder comes from the token, never from the body. Every
    date in the custody history comes from the injected clock, which RN04 will compare with."""

    def __init__(self, uow: UnitOfWork, clock: Clock):
        self._uow = uow
        self._clock = clock

    def register(
        self,
        actor: User,
        category_id: int,
        location_id: int,
        color_id: int,
        collection_point_id: int,
        description: str,
        found_date: date,
        questions: Sequence[tuple[str, str]],
    ) -> Item:
        # look before pointing: a missing id is a 404, not a foreign key error (500)
        if self._uow.categories.get(category_id) is None:
            raise CategoryNotFound()
        if self._uow.locations.get(location_id) is None:
            raise LocationNotFound()
        if self._uow.colors.get(color_id) is None:
            raise ColorNotFound()
        if self._uow.collection_points.get(collection_point_id) is None:
            raise CollectionPointNotFound()
        item = Item(
            category_id=category_id,
            location_id=location_id,
            color_id=color_id,
            collection_point_id=collection_point_id,
            finder_id=actor.id,
            description=description,
            found_date=found_date,
        )
        # RN20: positions 1, 2, ... in the order the finder wrote them
        item.questions = [
            ItemQuestion(position=n, question=q, answer=a)
            for n, (q, a) in enumerate(questions, start=1)
        ]
        # RN42: the first line is the item's birth, not an arrow, so transition_to doesn't write it
        item.history = [
            CustodyRecord(
                event=CustodyEvent.REGISTRATION,
                collection_point_id=collection_point_id,
                actor_id=actor.id,
                at=self._clock.now(),
            )
        ]
        self._uow.items.add(item)
        # one commit: the item, its questions and its first line are saved together, or nothing is
        self._uow.commit()
        return item

    def receive(self, actor: User, item_id: int, collection_point_id: int) -> Item:
        # RN41: the attendant works at the counter where the object is handed in; an admin anywhere
        ensure(can_operate_item(actor, collection_point_id, self._point_ids(actor)))
        if self._uow.collection_points.get(collection_point_id) is None:
            raise CollectionPointNotFound()
        item = self._uow.items.get_for_update(item_id)
        if item is None:
            raise ItemNotFound()
        # RN02: the item moves to this point; a second receipt is an InvalidTransition (409)
        item.receive(collection_point_id, by=actor.id, at=self._clock.now())
        self._uow.commit()
        return item

    def history(self, actor: User, item_id: int) -> Sequence[CustodyRecord]:
        # RN53: only the staff sees the history
        ensure(can_view_custody(actor))
        if self._uow.items.get(item_id) is None:
            raise ItemNotFound()
        return self._uow.custody.list_by_item(item_id)

    def list_public(
        self,
        *,
        q: str | None,
        category_id: int | None,
        location_id: int | None,
        found_from: date | None,
        found_to: date | None,
    ) -> Sequence[Item]:
        # public: no ensure; read-only: no commit
        return self._uow.items.search_public(
            q=q,
            category_id=category_id,
            location_id=location_id,
            found_from=found_from,
            found_to=found_to,
        )

    def _point_ids(self, actor: User) -> set[int]:
        return self._uow.collection_point_attendants.point_ids_of(actor.id)
