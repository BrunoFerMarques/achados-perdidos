from collections.abc import Sequence

from models import Category
from repositories.unit_of_work import UnitOfWork


class CategoryService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    def list_all(self) -> Sequence[Category]:
        return self._uow.categories.list_all()
