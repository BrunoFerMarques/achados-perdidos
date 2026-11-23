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
from models import Claim, Item, ItemQuestion, User
from repositories.unit_of_work import UnitOfWork


class ClaimService:
    """Reivindicações, análise do atendente e retirada no balcão. Todas as datas vêm do relógio
    injetável, o mesmo que o domain/blocking.py e o domain/pickup.py recebem como `now`."""

    def __init__(self, uow: UnitOfWork, clock: Clock):
        self._uow = uow
        self._clock = clock

    def create(self, actor: User, item_id: int, answers: Sequence[str]) -> Claim:
        ensure(can_claim(actor))
        # trava o usuário pra processar uma reivindicação dele por vez; sem isso, uma rajada de
        # pedidos leria a mesma contagem e passaria dos limites
        self._uow.users.lock(actor.id)
        item = self._claimable_item(actor, item_id)
        if len(answers) != len(item.questions):
            raise WrongAnswerCount()
        now = self._clock.now()
        self._ensure_may_try(actor, item, now)
        if self._uow.claims.count_active(actor.id) >= MAX_ACTIVE_CLAIMS:
            raise TooManyActiveClaims()

        value = score(answers, [q.answer for q in item.questions])
        claim = Claim.submit(item, actor.id, answers, value, at=now)
        self._uow.claims.add(claim)
        self._uow.commit()
        return claim

    def questions(self, actor: User, item_id: int) -> Sequence[ItemQuestion]:
        # só mostra as perguntas pra quem poderia reivindicar (a listagem pública não mostra).
        # O limite de ativas fica de fora porque dá pra cancelar outra antes de enviar
        ensure(can_claim(actor))
        item = self._claimable_item(actor, item_id)
        self._ensure_may_try(actor, item, self._clock.now())
        return item.questions

    def list_mine(self, actor: User) -> Sequence[Claim]:
        return self._uow.claims.list_by_claimant(actor.id)

    def cancel(self, actor: User, claim_id: int) -> Claim:
        claim = self._uow.claims.get_for_update(claim_id)
        # reivindicação de outra pessoa dá 404, pra não revelar quem reivindicou o quê
        if claim is None or not can_cancel_claim(actor, claim.claimant_id):
            raise ClaimNotFound()
        claim.cancel(by=actor.id, at=self._clock.now())
        self._uow.commit()
        return claim

    def list_pending(self, actor: User) -> Sequence[Claim]:
        return self._uow.claims.list_pending(self._staff_point_ids(actor), staff_id=actor.id)

    def list_approved(self, actor: User) -> Sequence[Claim]:
        # fila do balcão: quem pode vir buscar qual item
        return self._uow.claims.list_approved(self._staff_point_ids(actor), staff_id=actor.id)

    def approve(self, actor: User, claim_id: int) -> Claim:
        claim = self._find_for_staff(actor, claim_id)
        # só aprova com o item na prateleira, sem reserva pra outra pessoa
        if claim.item.status != ItemStatus.AVAILABLE:
            raise ItemNotAvailable()
        claim.approve(by=actor.id, at=self._clock.now(), pickup_code=generate_code())  # RN44
        # reivindicação e item mudam no mesmo commit
        self._uow.commit()
        return claim

    def reject(self, actor: User, claim_id: int) -> Claim:
        claim = self._find_for_staff(actor, claim_id)
        # rejeição do atendente conta como tentativa falha
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
        # permissão checada no ponto do item; se o balcão é o certo, quem confere é o domínio
        claim = self._find_for_staff(actor, claim_id)
        now = self._clock.now()
        claim.pick_up(
            pickup_code,
            point_id=collection_point_id,
            document_checked=document_checked,
            by=actor.id,
            at=now,
        )
        # o item foi pro dono, então as outras pendentes são rejeitadas com um motivo que não
        # conta como falha
        for other in self._uow.claims.lock_pending_by_item(claim.item_id):
            other.reject(RejectionReason.ITEM_RETURNED, at=now)
        # tudo no mesmo commit (reivindicação, item, histórico e as outras reivindicações)
        self._uow.commit()
        return claim

    def _staff_point_ids(self, actor: User) -> set[int] | None:
        # pontos que o atendente atende (None = todos, caso do admin)
        ensure(can_review_claims(actor))
        return None if operates_every_point(actor) else self._point_ids(actor)

    def _find_for_staff(self, actor: User, claim_id: int) -> Claim:
        # checa o papel antes pra não revelar quais ids existem
        ensure(can_review_claims(actor))
        claim = self._uow.claims.get_for_update(claim_id)
        if claim is None:
            raise ClaimNotFound()
        # trava o item também, depois da reivindicação, pra esperar um envio ou recebimento que
        # esteja rodando e ler o ponto e o status atualizados
        self._uow.items.get_for_update(claim.item_id)
        # 403 e não 404: atendente é da equipe, saber que a reivindicação existe em outro ponto
        # não expõe nada
        ensure(
            can_review_claim(
                actor, claim.claimant_id, claim.collection_point_id, self._point_ids(actor)
            )
        )
        return claim

    def _claimable_item(self, actor: User, item_id: int) -> Item:
        item = self._uow.items.get(item_id)
        if item is None:
            raise ItemNotFound()
        if item.finder_id == actor.id:
            raise OwnItemClaim()
        if not accepts_claims(item.status):
            raise ItemNotClaimable()
        return item

    def _ensure_may_try(self, actor: User, item: Item, now: datetime) -> None:
        if self._is_blocked(actor, now):
            raise ClaimingBlocked()
        if self._uow.claims.has_blocking_claim(item.id, actor.id):
            raise ItemAlreadyClaimed()

    def _point_ids(self, actor: User) -> set[int]:
        return self._uow.collection_point_attendants.point_ids_of(actor.id)

    def _is_blocked(self, actor: User, now: datetime) -> bool:
        failures = [
            at
            for at, reason in self._uow.claims.rejections_of(actor.id)
            if counts_as_failure(RejectionReason(reason))
        ]
        return is_blocked(failures, now, actor.unblocked_at)
