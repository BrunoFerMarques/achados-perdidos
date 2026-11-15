"""Found items (scope §5): their statuses and how many verification questions they take."""

from enum import StrEnum


class ItemStatus(StrEnum):
    REGISTERED = "registrado"
    AVAILABLE = "disponivel"
    IN_TRANSFER = "em_transferencia"
    RESERVED = "reservado"
    RETURNED = "devolvido"
    EXPIRED = "expirado"
    DISPOSED = "destinado"
    CANCELLED = "cancelado"


# RN20, scope §12: every item has from 2 to 5 verification questions
MIN_QUESTIONS = 2
MAX_QUESTIONS = 5