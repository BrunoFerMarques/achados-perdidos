"""Relógio injetável, pra nenhuma regra chamar datetime.now() direto."""

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    """Relógio real, usado fora dos testes."""

    def now(self) -> datetime:
        return datetime.now(UTC)
