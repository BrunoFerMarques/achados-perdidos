from collections.abc import Sequence
from datetime import date

from domain.clock import Clock
from domain.custody import CustodyEvent
from domain.errors import (
    CategoryNotFound,
    CollectionPointNotFound,
    ColorNotFound,
    ItemNotFound,
    ItemNotInTransfer,
    LocationNotFound,
)
from domain.permissions import (
    can_operate_item,
    can_receive_items,
    can_transfer_items,
    can_view_custody,
    ensure,
    operates_every_point,
)
from models import CustodyRecord, Item, ItemQuestion, User
from repositories.unit_of_work import UnitOfWork


class ItemService:
    """Itens achados e transferência entre pontos. O achador vem do token, nunca do corpo, e as
    datas do histórico vêm do relógio injetável."""

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

    def receive(
        self, actor: User, item_id: int, collection_point_id: int, description: str | None = None
    ) -> Item:
        # RN41: the attendant works at the counter where the object is handed in; an admin anywhere
        ensure(can_operate_item(actor, collection_point_id, self._point_ids(actor)))
        if self._uow.collection_points.get(collection_point_id) is None:
            raise CollectionPointNotFound()
        item = self._lock_item(item_id)
        # RN02: the item moves to this point; a second receipt is an InvalidTransition (409)
        item.receive(collection_point_id, by=actor.id, at=self._clock.now())
        # RN51: after the arrow, so a refused receipt leaves the description as it was
        if description is not None:
            item.description = description
        self._uow.commit()
        return item

    def list_registered(self, actor: User) -> Sequence[Item]:
        # RN02: what is waiting for a counter, for the whole staff
        ensure(can_receive_items(actor))
        return self._uow.items.list_registered()

    def list_mine(self, actor: User) -> Sequence[Item]:
        # RN53: no ensure, everyone follows the items they registered; the actor comes from the
        # token, so nobody asks for someone else's
        return self._uow.items.list_by_finder(actor.id)

    def transfer(self, actor: User, item_id: int, transfer_to_id: int) -> Item:
        # checa o papel antes pra usuário comum não travar a linha nem descobrir nada do item
        ensure(can_transfer_items(actor))
        item = self._lock_item(item_id)
        # quem envia tem que trabalhar no ponto onde o item está
        ensure(can_operate_item(actor, item.collection_point_id, self._point_ids(actor)))
        if self._uow.collection_points.get(transfer_to_id) is None:
            raise CollectionPointNotFound()
        # o model recusa se não estiver na prateleira ou se for pro mesmo ponto
        item.transfer_to(transfer_to_id, by=actor.id, at=self._clock.now())
        self._uow.commit()
        return item

    def arrive(self, actor: User, item_id: int) -> Item:
        ensure(can_transfer_items(actor))
        item = self._lock_item(item_id)
        # antes da permissão, porque sem destino não tem ponto pra checar
        if item.transfer_to_id is None:
            raise ItemNotInTransfer()
        # quem confirma a chegada tem que trabalhar no destino
        ensure(can_operate_item(actor, item.transfer_to_id, self._point_ids(actor)))
        item.arrive(by=actor.id, at=self._clock.now())
        self._uow.commit()
        return item

    def list_in_transfer(self, actor: User) -> Sequence[Item]:
        ensure(can_transfer_items(actor))
        point_ids = None if operates_every_point(actor) else self._point_ids(actor)
        return self._uow.items.list_in_transfer(point_ids)

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

    def _lock_item(self, item_id: int) -> Item:
        # trava até o commit, então duas operações no mesmo item rodam em fila
        item = self._uow.items.get_for_update(item_id)
        if item is None:
            raise ItemNotFound()
        return item

    def _point_ids(self, actor: User) -> set[int]:
        return self._uow.collection_point_attendants.point_ids_of(actor.id)
