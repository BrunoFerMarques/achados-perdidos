from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from domain.custody import EVENTS
from domain.items import ItemStatus, transition
from models.base import Base
from models.custody import CustodyRecord


class Item(Base):
    """A found object (scope §4.1). The column names are what domain/match.py reads."""

    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("btrim(description) <> ''", name="description"),
        CheckConstraint(
            "status IN ('registrado', 'disponivel', 'em_transferencia', 'reservado', "
            "'devolvido', 'expirado', 'destinado', 'cancelado')",
            name="status",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("categories.id"))
    location_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("locations.id"))
    color_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("colors.id"))
    collection_point_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("collection_points.id"))
    # SET NULL: deleting the account keeps the item, which is still on a shelf somewhere
    finder_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    description: Mapped[str]
    # only the day: the finder knows the day, not the time, and the match subtracts dates
    found_date: Mapped[date]
    status: Mapped[str] = mapped_column(server_default=ItemStatus.REGISTERED)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # in position order, so score() compares each answer with its own question
    questions: Mapped[list["ItemQuestion"]] = relationship(
        cascade="all, delete-orphan", order_by="ItemQuestion.position"
    )
    # the custody history, oldest first; no delete-orphan: a line never leaves the book (RN43)
    history: Mapped[list[CustodyRecord]] = relationship(order_by=CustodyRecord.id)

    def transition_to(self, target: ItemStatus, *, by: int | None, at: datetime) -> None:
        # RN01: the only way to change the status; outside the diagram it raises InvalidTransition
        current = self.status
        self.status = transition(current, target)
        # RN06: every status change writes one line, at the point where the item is now
        self.history.append(
            CustodyRecord(
                event=EVENTS[(current, target)],
                collection_point_id=self.collection_point_id,
                actor_id=by,
                at=at,
            )
        )

    def receive(self, point_id: int, *, by: int, at: datetime) -> None:
        # RN02: the item now belongs to the point where it was handed in, and the line says so
        self.collection_point_id = point_id
        self.transition_to(ItemStatus.AVAILABLE, by=by, at=at)


class ItemQuestion(Base):
    """A verification question (RN20) and its expected answer. Never public (RN23)."""

    __tablename__ = "item_questions"

    # a question means nothing without its item
    item_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str]
    # plain text: the typo tolerance and the attendant (RN22) need to read it
    answer: Mapped[str]
