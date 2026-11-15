from collections.abc import Sequence
from datetime import date

from domain.errors import (
    CategoryNotFound,
    CollectionPointNotFound,
    ColorNotFound,
    LocationNotFound,
)
from models import Item, ItemQuestion, User
from repositories.unit_of_work import UnitOfWork


class ItemService:
    """Found items (scope §4.1). The finder comes from the token, never from the body."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

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
        self._uow.items.add(item)
        # one commit: the item and its questions are saved together, or nothing is
        self._uow.commit()
        return item
