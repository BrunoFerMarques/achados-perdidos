from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from domain.items import ItemStatus
from models.base import Base


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
    collection_point_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("collection_points.id")
    )
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