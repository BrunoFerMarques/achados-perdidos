"""Custody history (scope §9): the kind of event each status change writes (RN06, RN42)."""

from enum import StrEnum

from domain.items import ItemStatus


class CustodyEvent(StrEnum):
    REGISTRATION = "registro"
    RECEIPT = "recebimento"
    TRANSFER_OUT = "transferencia_saida"
    TRANSFER_IN = "transferencia_chegada"
    RESERVATION = "reserva"
    RELEASE = "liberacao"
    RETURN = "devolucao"
    EXPIRATION = "expiracao"
    DISPOSAL = "destinacao"
    CANCELLATION = "cancelamento"


# RN06: the event each arrow of TRANSITIONS writes; REGISTRATION is the item's birth, not an arrow
EVENTS: dict[tuple[ItemStatus, ItemStatus], CustodyEvent] = {
    (ItemStatus.REGISTERED, ItemStatus.AVAILABLE): CustodyEvent.RECEIPT,
    (ItemStatus.REGISTERED, ItemStatus.CANCELLED): CustodyEvent.CANCELLATION,
    (ItemStatus.AVAILABLE, ItemStatus.IN_TRANSFER): CustodyEvent.TRANSFER_OUT,
    (ItemStatus.AVAILABLE, ItemStatus.RESERVED): CustodyEvent.RESERVATION,
    (ItemStatus.AVAILABLE, ItemStatus.EXPIRED): CustodyEvent.EXPIRATION,
    (ItemStatus.IN_TRANSFER, ItemStatus.AVAILABLE): CustodyEvent.TRANSFER_IN,
    # the pickup deadline passed or the claim was cancelled; RN42 had no name for it
    (ItemStatus.RESERVED, ItemStatus.AVAILABLE): CustodyEvent.RELEASE,
    (ItemStatus.RESERVED, ItemStatus.RETURNED): CustodyEvent.RETURN,
    (ItemStatus.EXPIRED, ItemStatus.DISPOSED): CustodyEvent.DISPOSAL,
}
