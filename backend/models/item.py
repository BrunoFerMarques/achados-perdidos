from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from domain.custody import EVENTS
from domain.errors import (
    InvalidTransition,
    ItemAlreadyAtThisPoint,
    ItemNotAvailable,
    ItemNotInTransfer,
)
from domain.items import ItemStatus, public_text, transition
from models.base import Base
from models.category import Category
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
        # destino só enquanto o item está em transferência, e nunca igual à origem
        CheckConstraint(
            "(status = 'em_transferencia') = (transfer_to_id IS NOT NULL) "
            "AND (transfer_to_id IS NULL OR transfer_to_id <> collection_point_id)",
            name="transfer_to_id",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("categories.id"))
    location_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("locations.id"))
    color_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("colors.id"))
    collection_point_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("collection_points.id"))
    # pra onde o item vai; collection_point_id continua sendo a origem até ele chegar
    transfer_to_id: Mapped[int | None] = mapped_column(
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

    # the way from category_id to the category's name; not a column, so no migration
    category: Mapped[Category] = relationship()
    # in position order, so score() compares each answer with its own question
    questions: Mapped[list["ItemQuestion"]] = relationship(
        cascade="all, delete-orphan", order_by="ItemQuestion.position"
    )
    # the custody history, oldest first; no delete-orphan: a line never leaves the book (RN43)
    history: Mapped[list[CustodyRecord]] = relationship(order_by=CustodyRecord.id)

    @property
    def public_description(self) -> str:
        # RN52: what the public listing shows instead of the description
        return public_text(self.category.name, self.description)

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
        # só item registrado pode ser recebido. Reservado e em transferência também voltam pra
        # DISPONIVEL no diagrama, mas por outros caminhos (reivindicação e arrive)
        if self.status != ItemStatus.REGISTERED:
            raise InvalidTransition()
        # RN02: the item now belongs to the point where it was handed in, and the line says so
        self.collection_point_id = point_id
        self.transition_to(ItemStatus.AVAILABLE, by=by, at=at)

    def transfer_to(self, point_id: int, *, by: int, at: datetime) -> None:
        # só sai da prateleira; item reservado fica esperando o dono
        if self.status != ItemStatus.AVAILABLE:
            raise ItemNotAvailable()
        if point_id == self.collection_point_id:
            raise ItemAlreadyAtThisPoint()
        # o destino vai antes da transição porque anexar o histórico pode dar autoflush, e a
        # constraint exige os dois juntos. A linha de saída ainda é gravada na origem
        self.transfer_to_id = point_id
        self.transition_to(ItemStatus.IN_TRANSFER, by=by, at=at)

    def arrive(self, *, by: int, at: datetime) -> None:
        # agora o item é do destino, e a linha de chegada é gravada lá
        if self.transfer_to_id is None:
            raise ItemNotInTransfer()
        self.collection_point_id, self.transfer_to_id = self.transfer_to_id, None
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
