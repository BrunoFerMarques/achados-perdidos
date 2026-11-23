from sqlalchemy.orm import Session

from models import Base


class Repository[T: Base]:
    """Acesso tipo coleção a um model. Consultas específicas ficam na subclasse."""

    model: type[T]

    def __init__(self, session: Session):
        self._session = session

    def add(self, entity: T) -> None:
        self._session.add(entity)

    def get(self, entity_id: int) -> T | None:
        return self._session.get(self.model, entity_id)

    def delete(self, entity: T) -> None:
        self._session.delete(entity)
