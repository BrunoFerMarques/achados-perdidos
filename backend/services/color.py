from collections.abc import Sequence

from models import Color
from repositories.unit_of_work import UnitOfWork


class ColorService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    def list_all(self) -> Sequence[Color]:
        return self._uow.colors.list_all()
