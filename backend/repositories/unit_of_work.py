from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.errors import (
    AttendantAlreadyLinked,
    CollectionPointNameExists,
    ConflictError,
    EmailAlreadyExists,
    ItemAlreadyClaimed,
    ItemNotAvailable,
)
from repositories.category import CategoryRepository
from repositories.claim import ClaimRepository
from repositories.collection_point import (
    CollectionPointAttendantRepository,
    CollectionPointRepository,
)
from repositories.color import ColorRepository
from repositories.custody import CustodyRepository
from repositories.item import ItemRepository
from repositories.location import LocationRepository
from repositories.lost_report import LostReportRepository
from repositories.user import UserRepository

# constraints únicas cuja violação é erro de negócio, não bug
CONFLICTS: dict[str, type[ConflictError]] = {
    "users_email_key": EmailAlreadyExists,
    "collection_points_name_key": CollectionPointNameExists,
    # the same attendant linked twice to the same point
    "collection_point_attendants_pkey": AttendantAlreadyLinked,
    # pedidos simultâneos que passaram juntos pela checagem do service
    "claims_claimant_item_key": ItemAlreadyClaimed,
    "claims_approved_item_key": ItemNotAvailable,
}


class UnitOfWork:
    """Uma transação: os repositories dividem a sessão e o commit salva tudo junto."""

    def __init__(self, session: Session):
        self._session = session
        self.users = UserRepository(session)
        self.categories = CategoryRepository(session)
        self.locations = LocationRepository(session)
        self.colors = ColorRepository(session)
        self.collection_points = CollectionPointRepository(session)
        self.items = ItemRepository(session)
        self.collection_point_attendants = CollectionPointAttendantRepository(session)
        self.lost_reports = LostReportRepository(session)
        self.claims = ClaimRepository(session)
        self.custody = CustodyRepository(session)

    def flush(self) -> None:
        # sends the pending changes inside the open transaction, without committing
        self._session.flush()

    def commit(self) -> None:
        try:
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            conflict = CONFLICTS.get(error.orig.diag.constraint_name)
            if conflict is None:
                raise
            raise conflict() from None
