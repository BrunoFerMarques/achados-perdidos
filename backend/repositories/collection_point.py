from collections.abc import Sequence

from sqlalchemy import select

from models import CollectionPoint, CollectionPointAttendant, User
from repositories.base import Repository


class CollectionPointRepository(Repository[CollectionPoint]):
    model = CollectionPoint

    def list_all(self) -> Sequence[CollectionPoint]:
        stmt = select(CollectionPoint).order_by(CollectionPoint.name)
        return self._session.scalars(stmt).all()


class CollectionPointAttendantRepository(Repository[CollectionPointAttendant]):
    """The link has a two-column key, so it gets its own lookups instead of get(id)."""

    model = CollectionPointAttendant

    def get_link(self, point_id: int, user_id: int) -> CollectionPointAttendant | None:
        return self._session.get(CollectionPointAttendant, (point_id, user_id))

    def list_attendants(self, point_id: int) -> Sequence[User]:
        stmt = (
            select(User)
            .join(CollectionPointAttendant, CollectionPointAttendant.user_id == User.id)
            .where(CollectionPointAttendant.point_id == point_id)
            .order_by(User.name)
        )
        return self._session.scalars(stmt).all()

    def point_ids_of(self, user_id: int) -> set[int]:
        # RN41 (etapa 08) checks an item's point against this set
        stmt = select(CollectionPointAttendant.point_id).where(
            CollectionPointAttendant.user_id == user_id
        )
        return set(self._session.scalars(stmt))
