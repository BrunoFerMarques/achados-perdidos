"""The current time as a dependency, so no rule reads the system clock directly (scope §15)."""

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    """The real clock, used outside the tests."""

    def now(self) -> datetime:
        return datetime.now(UTC)
