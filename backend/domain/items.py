"""Found items (scope §5): their statuses, where each one may go next and how many verification
questions they take."""

from enum import StrEnum

from domain.errors import InvalidTransition


class ItemStatus(StrEnum):
    REGISTERED = "registrado"
    AVAILABLE = "disponivel"
    IN_TRANSFER = "em_transferencia"
    RESERVED = "reservado"
    RETURNED = "devolvido"
    EXPIRED = "expirado"
    DISPOSED = "destinado"
    CANCELLED = "cancelado"


# RN01: where each status may go next; a status that isn't a key here is final
TRANSITIONS: dict[ItemStatus, frozenset[ItemStatus]] = {
    # received at the collection point, or cancelled before that
    ItemStatus.REGISTERED: frozenset({ItemStatus.AVAILABLE, ItemStatus.CANCELLED}),
    # sent to another point, reserved for an approved claim, or 60 days without an owner
    ItemStatus.AVAILABLE: frozenset(
        {ItemStatus.IN_TRANSFER, ItemStatus.RESERVED, ItemStatus.EXPIRED}
    ),
    # arrived at the new point
    ItemStatus.IN_TRANSFER: frozenset({ItemStatus.AVAILABLE}),
    # the pickup deadline passed, or the owner picked it up
    ItemStatus.RESERVED: frozenset({ItemStatus.AVAILABLE, ItemStatus.RETURNED}),
    # donated or discarded
    ItemStatus.EXPIRED: frozenset({ItemStatus.DISPOSED}),
}


def transition(current: ItemStatus, target: ItemStatus) -> ItemStatus:
    if target not in TRANSITIONS.get(current, frozenset()):
        raise InvalidTransition()
    return target


# RN20, scope §12: every item has from 2 to 5 verification questions
MIN_QUESTIONS = 2
MAX_QUESTIONS = 5
