"""Lost-item report states, transitions, and expiration rules (scope §8, RN33)."""

from datetime import datetime, timedelta
from enum import StrEnum

from domain.errors import InvalidTransition

REPORT_EXPIRATION = timedelta(days=60)


class LostReportStatus(StrEnum):
    ATIVO = "ativo"
    ENCERRADO = "encerrado"
    EXPIRADO = "expirado"


# Only ATIVO can move to another state; ENCERRADO and EXPIRADO are final states.
ALLOWED_TRANSITIONS: dict[LostReportStatus, frozenset[LostReportStatus]] = {
    LostReportStatus.ATIVO: frozenset({LostReportStatus.ENCERRADO, LostReportStatus.EXPIRADO}),
    LostReportStatus.ENCERRADO: frozenset(),
    LostReportStatus.EXPIRADO: frozenset(),
}


def can_transition(current: LostReportStatus, target: LostReportStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def ensure_transition(current: LostReportStatus, target: LostReportStatus) -> None:
    if not can_transition(current, target):
        raise InvalidTransition()


def is_expired(created_at: datetime, now: datetime) -> bool:
    """RN33: an ATIVO report expires 60 days after creation (on day 60, not day 59)."""
    return (now.date() - created_at.date()) >= REPORT_EXPIRATION
