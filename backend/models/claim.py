from collections.abc import Sequence
from datetime import datetime
from typing import Self

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from domain import pickup
from domain.claims import (
    RECLAIM_BLOCKING_STATUSES,
    ClaimStatus,
    RejectionReason,
    initial_status,
    transition,
)
from domain.items import ItemStatus
from domain.verification import passes
from models.base import Base
from models.item import Item


class Claim(Base):
    """Someone saying a found item is theirs (scope §6), with the answers they gave (§7)."""

    __tablename__ = "claims"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pendente', 'aprovada', 'rejeitada', 'cancelada', 'concluida', 'expirada')",
            name="status",
        ),
        CheckConstraint(
            "rejection_reason IN ('nota_baixa', 'atendente', 'item_devolvido')",
            name="rejection_reason",
        ),
        CheckConstraint("score BETWEEN 0 AND 1", name="score"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    # a claim means nothing without its item or its claimant
    item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("items.id", ondelete="CASCADE"))
    claimant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # no server default: the score decides whether it starts pending or rejected
    status: Mapped[str]
    # share of correct answers (§7); only the attendant sees it (RN21, RN22)
    score: Mapped[float]
    rejection_reason: Mapped[str | None]
    # both from the injected clock: blocking.py and pickup.py compare them with clock.now()
    rejected_at: Mapped[datetime | None]
    approved_at: Mapped[datetime | None]
    pickup_code: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    item: Mapped[Item] = relationship()
    # in position order, like Item.questions, so each answer sits next to its question
    answers: Mapped[list["ClaimAnswer"]] = relationship(
        cascade="all, delete-orphan", order_by="ClaimAnswer.position"
    )

    @classmethod
    def submit(
        cls, item: Item, claimant_id: int, answers: Sequence[str], score: float, *, at: datetime
    ) -> Self:
        """A new claim, already scored: below the minimum it starts rejected (§7)."""
        passed = passes(score)
        claim = cls(
            item_id=item.id,
            claimant_id=claimant_id,
            score=score,
            status=initial_status(passed),
            answers=[
                ClaimAnswer(position=q.position, answer=a)
                for q, a in zip(item.questions, answers, strict=True)
            ],
        )
        if not passed:
            # nobody reviews it, and it counts as a failed attempt (RN15)
            claim._record_rejection(RejectionReason.LOW_SCORE, at)
        return claim

    @property
    def collection_point_id(self) -> int:
        # RN53: the claimant learns where to pick the item up
        return self.item.collection_point_id

    @property
    def pickup_deadline(self) -> datetime | None:
        return None if self.approved_at is None else pickup.pickup_deadline(self.approved_at)

    def transition_to(self, target: ClaimStatus) -> None:
        # RN01: outside the diagram it raises InvalidTransition
        self.status = transition(self.status, target)

    def approve(self, *, by: int, at: datetime, pickup_code: str) -> None:
        self.transition_to(ClaimStatus.APPROVED)
        self.approved_at = at
        self.pickup_code = pickup_code
        self.item.transition_to(ItemStatus.RESERVED, by=by, at=at)  # RN13

    def reject(self, reason: RejectionReason, *, at: datetime) -> None:
        self.transition_to(ClaimStatus.REJECTED)
        self._record_rejection(reason, at)

    def cancel(self, *, by: int, at: datetime) -> None:
        was_approved = self.status == ClaimStatus.APPROVED
        self.transition_to(ClaimStatus.CANCELLED)
        if was_approved:
            # the item was waiting for this claimant; it goes back on the shelf
            self.item.transition_to(ItemStatus.AVAILABLE, by=by, at=at)

    def _record_rejection(self, reason: RejectionReason, at: datetime) -> None:
        # blocking.py counts the failures by rejected_at, so it is never left out
        self.rejection_reason = reason
        self.rejected_at = at


class ClaimAnswer(Base):
    """What the claimant answered to one verification question; the attendant reads it (RN22)."""

    __tablename__ = "claim_answers"

    claim_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True
    )
    # the position of the item question it answers
    position: Mapped[int] = mapped_column(primary_key=True)
    answer: Mapped[str]


# RN11: one active claim per user and item, and none after a rejection, even when several requests
# arrive together (otherwise a burst of claims would try many answers before any is rejected)
Index(
    "claims_claimant_item_key",
    Claim.item_id,
    Claim.claimant_id,
    unique=True,
    postgresql_where=Claim.status.in_(sorted(RECLAIM_BLOCKING_STATUSES)),
)
# RN13: at most one approved claim per item at a time
Index(
    "claims_approved_item_key",
    Claim.item_id,
    unique=True,
    postgresql_where=Claim.status == ClaimStatus.APPROVED,
)
