from collections.abc import Sequence

from sqlalchemy import select

from models import Category
from repositories.base import Repository


class CategoryRepository(Repository[Category]):
    model = Category

    def list_all(self) -> Sequence[Category]:
        stmt = select(Category).order_by(Category.name)
        return self._session.scalars(stmt).all()
