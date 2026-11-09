"""Claims (scope §6): someone saying a found item is theirs."""

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
    LOW_SCORE = "nota_baixa"  # below the minimum verification score, rejected at once
    ATTENDANT = "atendente"  # the attendant reviewed it and said no
    ITEM_RETURNED = "item_devolvido"  # RN14: the item went to someone else


# where each status may go next; a status that isn't a key here is final
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
    # below the minimum score there's nothing for an attendant to review
    return ClaimStatus.PENDING if passed_verification else ClaimStatus.REJECTED


def is_active(status: ClaimStatus) -> bool:
    return status in (ClaimStatus.PENDING, ClaimStatus.APPROVED)
