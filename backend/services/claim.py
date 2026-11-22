from collections.abc import Sequence
from datetime import datetime

from domain.blocking import counts_as_failure, is_blocked
from domain.claims import MAX_ACTIVE_CLAIMS, RejectionReason
from domain.clock import Clock
from domain.errors import (
    ClaimingBlocked,
    ClaimNotFound,
    ItemAlreadyClaimed,
    ItemNotAvailable,
    ItemNotClaimable,
    ItemNotFound,
    OwnItemClaim,
    TooManyActiveClaims,
    WrongAnswerCount,
)
from domain.items import ItemStatus, accepts_claims
from domain.permissions import (
    can_cancel_claim,
    can_claim,
    can_review_claim,
    can_review_claims,
    ensure,
    operates_every_point,
)
from domain.pickup import generate_code
from domain.verification import score
from models import Claim, User
from repositories.unit_of_work import UnitOfWork


class ClaimService:
    """Claims (scope §6), their review by an attendant and the pickup at the counter (RN14, RN44
    to RN46). Every date comes from the injected
    clock, the same one domain/blocking.py and domain/pickup.py are given as `now`."""

    def __init__(self, uow: UnitOfWork, clock: Clock):
        self._uow = uow
        self._clock = clock

    def create(self, actor: User, item_id: int, answers: Sequence[str]) -> Claim:
        ensure(can_claim(actor))
        # one claim at a time per user: the limits below are counted from the database, and a
        # burst of requests would otherwise all read the same count (RN11, RN12, RN15)
        self._uow.users.lock(actor.id)
        item = self._uow.items.get(item_id)
        if item is None:
            raise ItemNotFound()
        if len(answers) != len(item.questions):
            raise WrongAnswerCount()
        if item.finder_id == actor.id:
            raise OwnItemClaim()  # RN10
        if not accepts_claims(item.status):
            raise ItemNotClaimable()
        now = self._clock.now()
        if self._is_blocked(actor, now):
            raise ClaimingBlocked()  # RN15
        if self._uow.claims.has_blocking_claim(item.id, actor.id):
            raise ItemAlreadyClaimed()  # RN11
        if self._uow.claims.count_active(actor.id) >= MAX_ACTIVE_CLAIMS:
            raise TooManyActiveClaims()  # RN12

        value = score(answers, [q.answer for q in item.questions])
        claim = Claim.submit(item, actor.id, answers, value, at=now)
        self._uow.claims.add(claim)
        self._uow.commit()
        return claim

    def list_mine(self, actor: User) -> Sequence[Claim]:
        return self._uow.claims.list_by_claimant(actor.id)

    def cancel(self, actor: User, claim_id: int) -> Claim:
        claim = self._uow.claims.get_for_update(claim_id)
        # someone else's claim looks like a missing one: an id doesn't tell who claimed what
        if claim is None or not can_cancel_claim(actor, claim.claimant_id):
            raise ClaimNotFound()
        claim.cancel(by=actor.id, at=self._clock.now())
        self._uow.commit()
        return claim

    def list_pending(self, actor: User) -> Sequence[Claim]:
        return self._uow.claims.list_pending(self._staff_point_ids(actor), staff_id=actor.id)

    def list_approved(self, actor: User) -> Sequence[Claim]:
        # the counter's queue: who may come for which item (RN44 to RN46)
        return self._uow.claims.list_approved(self._staff_point_ids(actor), staff_id=actor.id)

    def approve(self, actor: User, claim_id: int) -> Claim:
        claim = self._find_for_staff(actor, claim_id)
        # RN13: the item must be on the shelf, and not reserved for another claim
        if claim.item.status != ItemStatus.AVAILABLE:
            raise ItemNotAvailable()
        claim.approve(by=actor.id, at=self._clock.now(), pickup_code=generate_code())  # RN44
        # one commit: the claim and the item change together, or neither does
        self._uow.commit()
        return claim

    def reject(self, actor: User, claim_id: int) -> Claim:
        claim = self._find_for_staff(actor, claim_id)
        # RN15: an attendant's rejection is a failed attempt
        claim.reject(RejectionReason.ATTENDANT, at=self._clock.now())
        self._uow.commit()
        return claim

    def pick_up(
        self,
        actor: User,
        claim_id: int,
        collection_point_id: int,
        pickup_code: str,
        document_checked: bool,
    ) -> Claim:
        # RN41 against the item's point; RN45 (the counter is that same point) is the domain's
        claim = self._find_for_staff(actor, claim_id)
        now = self._clock.now()
        claim.pick_up(
            pickup_code,
            point_id=collection_point_id,
            document_checked=document_checked,
            by=actor.id,
            at=now,
        )
        # RN14: the item went to its owner, so the others waiting for it are turned down; the
        # reason keeps it from counting as a failed attempt (RN15)
        for other in self._uow.claims.lock_pending_by_item(claim.item_id):
            other.reject(RejectionReason.ITEM_RETURNED, at=now)
        # one commit: the claim, the item, its history and the other claims change together
        self._uow.commit()
        return claim

    def _staff_point_ids(self, actor: User) -> set[int] | None:
        # the points whose claims the actor handles (RN41); None means every point (an admin)
        ensure(can_review_claims(actor))
        return None if operates_every_point(actor) else self._point_ids(actor)

    def _find_for_staff(self, actor: User, claim_id: int) -> Claim:
        # the role first, so a user can't tell which claim ids exist
        ensure(can_review_claims(actor))
        claim = self._uow.claims.get_for_update(claim_id)
        if claim is None:
            raise ClaimNotFound()
        # the item too, claim first: a transfer or a receipt at the same time waits, and RN41 and
        # RN13 read where the item is now, not where it was when the claim was loaded
        self._uow.items.get_for_update(claim.item_id)
        # RN41: 403, not 404; attendants are staff, and knowing a claim exists elsewhere is harmless
        ensure(
            can_review_claim(
                actor, claim.claimant_id, claim.collection_point_id, self._point_ids(actor)
            )
        )
        return claim

    def _point_ids(self, actor: User) -> set[int]:
        return self._uow.collection_point_attendants.point_ids_of(actor.id)

    def _is_blocked(self, actor: User, now: datetime) -> bool:
        failures = [
            at
            for at, reason in self._uow.claims.rejections_of(actor.id)
            if counts_as_failure(RejectionReason(reason))
        ]
        return is_blocked(failures, now, actor.unblocked_at)
