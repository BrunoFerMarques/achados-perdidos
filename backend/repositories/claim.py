from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Select, exists, func, select
from sqlalchemy.orm import selectinload

from domain.claims import ACTIVE_STATUSES, RECLAIM_BLOCKING_STATUSES, ClaimStatus
from models import Claim, Item
from repositories.base import Repository


class ClaimRepository(Repository[Claim]):
    model = Claim

    def get_for_update(self, claim_id: int) -> Claim | None:
        # trava a linha até o commit. Assim aprovar e cancelar a mesma reivindicação ao mesmo
        # tempo roda em fila, e o segundo vê o status que o primeiro deixou
        stmt = select(Claim).where(Claim.id == claim_id).with_for_update()
        return self._session.scalars(stmt.execution_options(populate_existing=True)).one_or_none()

    def list_by_claimant(self, claimant_id: int) -> Sequence[Claim]:
        # traz o item junto porque o ClaimOut mostra o ponto de coleta
        stmt = (
            select(Claim)
            .where(Claim.claimant_id == claimant_id)
            .options(selectinload(Claim.item))
            .order_by(Claim.id.desc())
        )
        return self._session.scalars(stmt).all()

    def lock_active_by_claimant(self, claimant_id: int) -> Sequence[Claim]:
        # trava igual ao get_for_update: se uma aprovação rodar junto com a exclusão da conta,
        # ou ela termina antes ou espera e não acha mais a reivindicação
        stmt = (
            select(Claim)
            .where(Claim.claimant_id == claimant_id, Claim.status.in_(ACTIVE_STATUSES))
            .with_for_update()
        )
        return self._session.scalars(stmt.execution_options(populate_existing=True)).all()

    def count_active(self, claimant_id: int) -> int:
        stmt = select(func.count()).where(
            Claim.claimant_id == claimant_id, Claim.status.in_(ACTIVE_STATUSES)
        )
        return self._session.scalar(stmt)

    def has_blocking_claim(self, item_id: int, claimant_id: int) -> bool:
        # já tem uma ativa ou rejeitada nesse item?
        stmt = select(
            exists().where(
                Claim.item_id == item_id,
                Claim.claimant_id == claimant_id,
                Claim.status.in_(RECLAIM_BLOCKING_STATUSES),
            )
        )
        return self._session.scalar(stmt)

    def rejections_of(self, claimant_id: int) -> Sequence[tuple[datetime, str]]:
        # data e motivo de cada rejeição; o que conta como falha quem decide é o blocking.py
        stmt = select(Claim.rejected_at, Claim.rejection_reason).where(
            Claim.claimant_id == claimant_id, Claim.status == ClaimStatus.REJECTED
        )
        return self._session.execute(stmt).all()

    def lock_pending_by_item(self, item_id: int) -> Sequence[Claim]:
        # trava igual ao get_for_update pra não sobrescrever um cancelamento feito junto
        stmt = (
            select(Claim)
            .where(Claim.item_id == item_id, Claim.status == ClaimStatus.PENDING)
            .with_for_update()
        )
        return self._session.scalars(stmt.execution_options(populate_existing=True)).all()

    def list_pending(self, point_ids: set[int] | None, staff_id: int) -> Sequence[Claim]:
        # traz respostas e perguntas pra tela de análise
        stmt = self._for_staff(ClaimStatus.PENDING, point_ids, staff_id).options(
            selectinload(Claim.answers), selectinload(Claim.item).selectinload(Item.questions)
        )
        return self._session.scalars(stmt).all()

    def list_approved(self, point_ids: set[int] | None, staff_id: int) -> Sequence[Claim]:
        # traz item e reivindicante pro balcão (descrição pra achar o objeto, nome pra conferir
        # o documento). Aprovação com prazo vencido continua aqui até a tarefa de expiração rodar
        stmt = self._for_staff(ClaimStatus.APPROVED, point_ids, staff_id).options(
            selectinload(Claim.item), selectinload(Claim.claimant)
        )
        return self._session.scalars(stmt).all()

    @staticmethod
    def _for_staff(status: ClaimStatus, point_ids: set[int] | None, staff_id: int) -> Select:
        """Reivindicações com esse status, da mais antiga pra mais nova.

        `point_ids` filtra pelos pontos dos itens (None = todos). As reivindicações do próprio
        atendente ficam de fora."""
        stmt = (
            select(Claim)
            .join(Item)
            .where(Claim.status == status, Claim.claimant_id != staff_id)
            .order_by(Claim.id)
        )
        if point_ids is not None:
            stmt = stmt.where(Item.collection_point_id.in_(point_ids))
        return stmt
