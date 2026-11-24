"""Reivindicação de item achado."""

from enum import StrEnum

from domain.errors import InvalidTransition


class ClaimStatus(StrEnum):
    PENDING = "pendente"
    APPROVED = "aprovada"
    REJECTED = "rejeitada"
    CANCELLED = "cancelada"
    COMPLETED = "concluida"
    EXPIRED = "expirada"


class RejectionReason(StrEnum):
    LOW_SCORE = "nota_baixa"  # nota abaixo do mínimo, rejeitada na hora
    ATTENDANT = "atendente"  # o atendente rejeitou
    ITEM_RETURNED = "item_devolvido"  # o item foi entregue pra outra pessoa


# transições permitidas; status que não aparece como chave é final
TRANSITIONS: dict[ClaimStatus, frozenset[ClaimStatus]] = {
    ClaimStatus.PENDING: frozenset(
        {ClaimStatus.APPROVED, ClaimStatus.REJECTED, ClaimStatus.CANCELLED}
    ),
    ClaimStatus.APPROVED: frozenset(
        {ClaimStatus.COMPLETED, ClaimStatus.EXPIRED, ClaimStatus.CANCELLED}
    ),
}


def transition(current: ClaimStatus, target: ClaimStatus) -> ClaimStatus:
    if target not in TRANSITIONS.get(current, frozenset()):
        raise InvalidTransition()
    return target


def initial_status(passed_verification: bool) -> ClaimStatus:
    # com nota baixa nem vai pra análise
    return ClaimStatus.PENDING if passed_verification else ClaimStatus.REJECTED


# o que conta como reivindicação ativa
ACTIVE_STATUSES = frozenset({ClaimStatus.PENDING, ClaimStatus.APPROVED})
# não pode ter duas no mesmo item nem tentar de novo depois de rejeitada
RECLAIM_BLOCKING_STATUSES = ACTIVE_STATUSES | {ClaimStatus.REJECTED}
# limite de reivindicações ativas por usuário
MAX_ACTIVE_CLAIMS = 3
