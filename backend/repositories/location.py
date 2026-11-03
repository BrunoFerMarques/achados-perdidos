from collections.abc import Sequence

from sqlalchemy import select

from models import Location
from repositories.base import Repository


class LocationRepository(Repository[Location]):
    model = Location

    def list_all(self) -> Sequence[Location]:
        stmt = select(Location).order_by(Location.name)
        return self._session.scalars(stmt).all()
