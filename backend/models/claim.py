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
from models.user import User


class Claim(Base):
    """Alguém dizendo que um item achado é seu, junto com as respostas que deu."""

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
    # sem o item ou sem o usuário a reivindicação não faz sentido (CASCADE)
    item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("items.id", ondelete="CASCADE"))
    claimant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # sem default: a nota decide se ela começa pendente ou rejeitada
    status: Mapped[str]
    # fração de respostas certas, só o atendente vê
    score: Mapped[float]
    rejection_reason: Mapped[str | None]
    # vêm do relógio injetável, que é o que blocking.py e pickup.py usam pra comparar
    rejected_at: Mapped[datetime | None]
    approved_at: Mapped[datetime | None]
    pickup_code: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    item: Mapped[Item] = relationship()
    # o atendente usa o nome pra conferir o documento na retirada
    claimant: Mapped[User] = relationship()
    # em ordem de posição pra cada resposta bater com a pergunta
    answers: Mapped[list["ClaimAnswer"]] = relationship(
        cascade="all, delete-orphan", order_by="ClaimAnswer.position"
    )

    @classmethod
    def submit(
        cls, item: Item, claimant_id: int, answers: Sequence[str], score: float, *, at: datetime
    ) -> Self:
        """Cria a reivindicação já com a nota. Abaixo do mínimo ela já nasce rejeitada."""
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
            # ninguém analisa, e conta como tentativa falha
            claim._record_rejection(RejectionReason.LOW_SCORE, at)
        return claim

    @property
    def collection_point_id(self) -> int:
        # o reivindicante precisa saber onde retirar o item
        return self.item.collection_point_id

    @property
    def item_description(self) -> str:
        # a original, só pra equipe
        return self.item.description

    @property
    def item_public_description(self) -> str:
        # a mesma do mural (RN52): o reivindicante não pode ler o nome escrito num documento
        return self.item.public_description

    @property
    def pickup_deadline(self) -> datetime | None:
        return None if self.approved_at is None else pickup.pickup_deadline(self.approved_at)

    def transition_to(self, target: ClaimStatus) -> None:
        # transição fora do diagrama levanta InvalidTransition
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
            # o item estava reservado pra ele, então volta pra prateleira
            self.item.transition_to(ItemStatus.AVAILABLE, by=by, at=at)

    def pick_up(
        self, typed_code: str, *, point_id: int, document_checked: bool, by: int, at: datetime
    ) -> None:
        # o domínio confere código, prazo, balcão e documento
        self.transition_to(
            pickup.complete_pickup(
                self.status,
                code=self.pickup_code,
                typed_code=typed_code,
                deadline=self.pickup_deadline,
                item_point_id=self.collection_point_id,
                point_id=point_id,
                document_checked=document_checked,
                now=at,
            )
        )
        self.item.transition_to(ItemStatus.RETURNED, by=by, at=at)

    def _record_rejection(self, reason: RejectionReason, at: datetime) -> None:
        # o bloqueio conta as falhas pelo rejected_at, então ele tem que estar sempre preenchido
        self.rejection_reason = reason
        self.rejected_at = at


class ClaimAnswer(Base):
    """Resposta dada a uma pergunta de verificação (o atendente lê na análise)."""

    __tablename__ = "claim_answers"

    claim_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True
    )
    # posição da pergunta que ela responde
    position: Mapped[int] = mapped_column(primary_key=True)
    answer: Mapped[str]


# uma reivindicação ativa por usuário e item, e nenhuma depois de rejeitada. O índice segura
# pedidos simultâneos que passariam juntos pela checagem do service
Index(
    "claims_claimant_item_key",
    Claim.item_id,
    Claim.claimant_id,
    unique=True,
    postgresql_where=Claim.status.in_(sorted(RECLAIM_BLOCKING_STATUSES)),
)
# no máximo uma reivindicação aprovada por item
Index(
    "claims_approved_item_key",
    Claim.item_id,
    unique=True,
    postgresql_where=Claim.status == ClaimStatus.APPROVED,
)
