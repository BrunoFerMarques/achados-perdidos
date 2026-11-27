"""The custody history (scope §9): one line per event in an item's life (RN06, RN42)."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.user import User


class CustodyRecord(Base):
    """One event in an item's custody. Lines are only added, never edited or deleted (RN43)."""

    __tablename__ = "custody_records"
    __table_args__ = (
        CheckConstraint(
            "event IN ('registro', 'recebimento', 'transferencia_saida', "
            "'transferencia_chegada', 'reserva', 'liberacao', 'devolucao', 'expiracao', "
            "'destinacao', 'cancelamento')",
            name="event",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    # no ondelete: an item with a history is never deleted, or the history would go with it
    item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("items.id"), index=True)
    event: Mapped[str]
    # where the item was when it happened
    collection_point_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("collection_points.id"))
    # SET NULL: deleting the account keeps the line; None is also a deadline nobody acted on
    actor_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    # from the injected clock: RN04 will count the 60 days from the receipt
    at: Mapped[datetime]

    # the way from actor_id to the person's name; not a column, so no migration
    actor: Mapped[User | None] = relationship()

    @property
    def actor_name(self) -> str | None:
        return None if self.actor is None else self.actor.name
