"""Bloqueio por tentativas falhas."""

from collections.abc import Iterable
from datetime import datetime, timedelta

from domain.claims import RejectionReason

FAILURES_TO_BLOCK = 3
FAILURE_WINDOW = timedelta(days=30)
BLOCK_DURATION = timedelta(days=7)


def counts_as_failure(reason: RejectionReason) -> bool:
    # cancelada e expirada não são rejeição, então nem chegam aqui
    return reason != RejectionReason.ITEM_RETURNED


def is_blocked(
    failures: Iterable[datetime], now: datetime, unblocked_at: datetime | None = None
) -> bool:
    """`failures` = datas das rejeições que contam como falha.
    `unblocked_at` = último desbloqueio feito pelo admin.
    `now` vem de quem chama (relógio injetável)."""
    end = _block_end(failures, unblocked_at)
    return end is not None and now < end


def _block_end(failures: Iterable[datetime], unblocked_at: datetime | None) -> datetime | None:
    counted: list[datetime] = []
    end = None
    for failure in sorted(failures):
        if unblocked_at is not None and failure <= unblocked_at:
            continue  # o admin desbloqueou depois dessa falha
        counted = [f for f in counted if failure - f < FAILURE_WINDOW]
        counted.append(failure)
        if len(counted) >= FAILURES_TO_BLOCK:
            end = failure + BLOCK_DURATION
            counted = []  # essas já geraram um bloqueio, não contam de novo
    return end
