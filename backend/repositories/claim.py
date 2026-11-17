from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import exists, func, select
from sqlalchemy.orm import selectinload

from domain.claims import ACTIVE_STATUSES, RECLAIM_BLOCKING_STATUSES, ClaimStatus
from models import Claim, Item
from repositories.base import Repository


class ClaimRepository(Repository[Claim]):
    model = Claim

    def get_for_update(self, claim_id: int) -> Claim | None:
        # locks the row until the commit: an approval and a cancellation of the same claim at once
        # run one after the other, and the second one sees the status the first one left
        stmt = select(Claim).where(Claim.id == claim_id).with_for_update()
        return self._session.scalars(stmt.execution_options(populate_existing=True)).one_or_none()

    def list_by_claimant(self, claimant_id: int) -> Sequence[Claim]:
        # the item comes along: ClaimOut shows its collection point
        stmt = (
            select(Claim)
            .where(Claim.claimant_id == claimant_id)
            .options(selectinload(Claim.item))
            .order_by(Claim.id.desc())
        )
        return self._session.scalars(stmt).all()

    def lock_active_by_claimant(self, claimant_id: int) -> Sequence[Claim]:
        # locked like get_for_update: an approval racing an account deletion either lands first
        # and is seen here, or waits and then finds the claim gone
        stmt = (
            select(Claim)
            .where(Claim.claimant_id == claimant_id, Claim.status.in_(ACTIVE_STATUSES))
            .with_for_update()
        )
        return self._session.scalars(stmt.execution_options(populate_existing=True)).all()

    def count_active(self, claimant_id: int) -> int:
        # RN12
        stmt = select(func.count()).where(
            Claim.claimant_id == claimant_id, Claim.status.in_(ACTIVE_STATUSES)
        )
        return self._session.scalar(stmt)

    def has_blocking_claim(self, item_id: int, claimant_id: int) -> bool:
        # RN11: an active or rejected claim on the same item
        stmt = select(
            exists().where(
                Claim.item_id == item_id,
                Claim.claimant_id == claimant_id,
                Claim.status.in_(RECLAIM_BLOCKING_STATUSES),
            )
        )
        return self._session.scalar(stmt)

    def rejections_of(self, claimant_id: int) -> Sequence[tuple[datetime, str]]:
        # RN15: when and why each claim was rejected; domain/blocking.py decides which count
        stmt = select(Claim.rejected_at, Claim.rejection_reason).where(
            Claim.claimant_id == claimant_id, Claim.status == ClaimStatus.REJECTED
        )
        return self._session.execute(stmt).all()

    def list_pending(self, point_ids: set[int] | None, reviewer_id: int) -> Sequence[Claim]:
        """Pending claims, oldest first; `point_ids` limits them to items at those points (RN41),
        and None means every point. The reviewer's own claims are left out. The answers and
        questions come along for the review (RN22)."""
        stmt = (
            select(Claim)
            .join(Item)
            .where(Claim.status == ClaimStatus.PENDING, Claim.claimant_id != reviewer_id)
            .options(
                selectinload(Claim.answers), selectinload(Claim.item).selectinload(Item.questions)
            )
            .order_by(Claim.id)
        )
        if point_ids is not None:
            stmt = stmt.where(Item.collection_point_id.in_(point_ids))
        return self._session.scalars(stmt).all()
