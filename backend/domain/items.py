"""Found items (scope §5): their statuses, where each one may go next, how many verification
questions they take and what the public listing shows of them."""

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


# status que ainda aceitam reivindicação (na prateleira ou a caminho dela)
CLAIMABLE_STATUSES = frozenset({ItemStatus.AVAILABLE, ItemStatus.IN_TRANSFER})


def accepts_claims(status: ItemStatus) -> bool:
    return status in CLAIMABLE_STATUSES


# RN20, scope §12: every item has from 2 to 5 verification questions
MIN_QUESTIONS = 2
MAX_QUESTIONS = 5


# RN50: the statuses on the public listing; the item is at a collection point or on its way
PUBLIC_STATUSES = frozenset({ItemStatus.AVAILABLE, ItemStatus.IN_TRANSFER})


# RN52: a document's description has personal data, so the listing shows a fixed text instead;
# the name on the document goes into a verification question
DOCUMENTS_CATEGORY = "Documentos"
DOCUMENT_TEXT = "Documento de identificação"


def public_text(category: str, description: str) -> str:
    if category == DOCUMENTS_CATEGORY:
        return DOCUMENT_TEXT
    return description
