"""Código de retirada."""

import secrets
import string
from datetime import datetime, timedelta

from domain.claims import ClaimStatus, transition
from domain.errors import (
    DocumentNotChecked,
    InvalidPickupCode,
    ItemNotAtThisPoint,
    PickupCodeAlreadyUsed,
    PickupCodeExpired,
)

CODE_LENGTH = 6
PICKUP_WINDOW = timedelta(days=5)
ALPHABET = string.ascii_uppercase + string.digits


def generate_code() -> str:
    # secrets em vez de random porque quem acerta o código leva o item
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def normalize_code(code: str) -> str:
    # ignora maiúsculas e espaços nas pontas
    return code.strip().upper()


def pickup_deadline(approved_at: datetime) -> datetime:
    # vale por 5 dias a partir da aprovação
    return approved_at + PICKUP_WINDOW


def code_matches(code: str | None, typed: str) -> bool:
    # compare_digest com str quebra se tiver acento, por isso compara em bytes
    if code is None:
        return False
    return secrets.compare_digest(normalize_code(typed).encode(), code.encode())


def complete_pickup(
    status: ClaimStatus,
    *,
    code: str | None,
    typed_code: str,
    deadline: datetime | None,
    item_point_id: int,
    point_id: int,
    document_checked: bool,
    now: datetime,
) -> ClaimStatus:
    """Valida a retirada e devolve o novo status da reivindicação.

    `code` e `deadline` vêm None se ela nunca foi aprovada. `point_id` é o balcão onde o
    atendente está, e `now` vem de quem chama."""
    if not code_matches(code, typed_code):
        # confere o código antes de tudo pra não revelar se ele já foi usado
        raise InvalidPickupCode()
    if status == ClaimStatus.COMPLETED:
        raise PickupCodeAlreadyUsed()  # o código só vale uma vez
    if status == ClaimStatus.EXPIRED:
        raise PickupCodeExpired()
    if status != ClaimStatus.APPROVED or deadline is None:
        # cancelada ainda tem o código salvo, mas ele não vale mais
        raise InvalidPickupCode()
    if now >= deadline:
        raise PickupCodeExpired()  # a tarefa de expiração pode ainda não ter rodado
    if point_id != item_point_id:
        raise ItemNotAtThisPoint()
    if not document_checked:
        raise DocumentNotChecked()
    return transition(status, ClaimStatus.COMPLETED)
