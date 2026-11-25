from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import CustodyRecord


class CustodyRepository:
    """The custody history (RN43): lines are only added. It doesn't inherit Repository on
    purpose, because that would bring delete along."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, record: CustodyRecord) -> None:
        self._session.add(record)

    def list_by_item(self, item_id: int) -> Sequence[CustodyRecord]:
        # oldest first: the history is read in the order it happened. The people come along in
        # one query, or each line would ask for its own
        stmt = (
            select(CustodyRecord)
            .where(CustodyRecord.item_id == item_id)
            .options(selectinload(CustodyRecord.actor))
            .order_by(CustodyRecord.id)
        )
        return self._session.scalars(stmt).all()
