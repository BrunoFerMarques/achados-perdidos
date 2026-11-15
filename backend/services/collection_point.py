from collections.abc import Sequence

from domain.errors import (
    AttendantLinkNotFound,
    CollectionPointNotFound,
    UserIsNotAttendant,
    UserNotFound,
)
from domain.permissions import can_manage_collection_points, ensure
from domain.roles import Role
from models import CollectionPoint, CollectionPointAttendant, User
from repositories.unit_of_work import UnitOfWork


class CollectionPointService:
    """Collection points and their attendants (RN40). Only an admin changes them; the permission
    check comes first, so nobody else can tell which points or users exist."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    def list_all(self) -> Sequence[CollectionPoint]:
        # public: the finder picks a point when registering an item
        return self._uow.collection_points.list_all()

    def create(self, actor: User, name: str) -> CollectionPoint:
        ensure(can_manage_collection_points(actor))
        point = CollectionPoint(name=name)
        self._uow.collection_points.add(point)
        self._uow.commit()
        return point

    def list_attendants(self, actor: User, point_id: int) -> Sequence[User]:
        ensure(can_manage_collection_points(actor))
        self._find_point(point_id)
        return self._uow.collection_point_attendants.list_attendants(point_id)

    def link(self, actor: User, point_id: int, user_id: int) -> User:
        ensure(can_manage_collection_points(actor))
        self._find_point(point_id)
        user = self._uow.users.get(user_id)
        if user is None:
            raise UserNotFound()
        # an admin already operates every point, so only attendants are linked
        if user.role != Role.ATENDENTE:
            raise UserIsNotAttendant()
        self._uow.collection_point_attendants.add(
            CollectionPointAttendant(point_id=point_id, user_id=user_id)
        )
        self._uow.commit()
        return user

    def unlink(self, actor: User, point_id: int, user_id: int) -> None:
        ensure(can_manage_collection_points(actor))
        self._find_point(point_id)
        link = self._uow.collection_point_attendants.get_link(point_id, user_id)
        if link is None:
            raise AttendantLinkNotFound()
        self._uow.collection_point_attendants.delete(link)
        self._uow.commit()

    def _find_point(self, point_id: int) -> CollectionPoint:
        point = self._uow.collection_points.get(point_id)
        if point is None:
            raise CollectionPointNotFound()
        return point
