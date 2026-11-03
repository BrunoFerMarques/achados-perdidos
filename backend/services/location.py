from collections.abc import Sequence

from models import Location
from repositories.unit_of_work import UnitOfWork


class LocationService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    def list_all(self) -> Sequence[Location]:
        return self._uow.locations.list_all()
