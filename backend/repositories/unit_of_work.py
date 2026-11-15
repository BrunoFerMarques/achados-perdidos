from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.errors import (
    AttendantAlreadyLinked,
    CollectionPointNameExists,
    ConflictError,
    EmailAlreadyExists,
)
from repositories.category import CategoryRepository
from repositories.collection_point import (
    CollectionPointAttendantRepository,
    CollectionPointRepository,
)
from repositories.color import ColorRepository
from repositories.location import LocationRepository
from repositories.user import UserRepository

# unique constraints whose violation is a business error, not a bug
CONFLICTS: dict[str, type[ConflictError]] = {
    "users_email_key": EmailAlreadyExists,
    "collection_points_name_key": CollectionPointNameExists,
    # the same attendant linked twice to the same point
    "collection_point_attendants_pkey": AttendantAlreadyLinked,
}


class UnitOfWork:
    """One business transaction: every repository shares the session and commit saves it all."""

    def __init__(self, session: Session):
        self._session = session
        self.users = UserRepository(session)
        self.categories = CategoryRepository(session)
        self.locations = LocationRepository(session)
        self.colors = ColorRepository(session)
        self.collection_points = CollectionPointRepository(session)
        self.collection_point_attendants = CollectionPointAttendantRepository(session)

    def commit(self) -> None:
        try:
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            conflict = CONFLICTS.get(error.orig.diag.constraint_name)
            if conflict is None:
                raise
            raise conflict() from None
