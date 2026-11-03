from collections.abc import Sequence

from sqlalchemy import select

from models import Color
from repositories.base import Repository


class ColorRepository(Repository[Color]):
    model = Color

    def list_all(self) -> Sequence[Color]:
        stmt = select(Color).order_by(Color.name)
        return self._session.scalars(stmt).all()
