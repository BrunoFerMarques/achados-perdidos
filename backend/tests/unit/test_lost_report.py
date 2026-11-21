from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from domain.errors import InvalidTransition
from domain.lost_reports import (
    LostReportStatus,
    can_transition,
    ensure_transition,
    is_expired,
)
from domain.permissions import (
    can_access_lost_report,
    can_create_lost_report,
    can_list_lost_reports,
)
from domain.roles import Role


@dataclass
class FakeActor:
    id: int
    role: str


# --- §8: máquina de estados (grade 3x3) ---

ALL_STATUSES = [
    LostReportStatus.ATIVO,
    LostReportStatus.ENCERRADO,
    LostReportStatus.EXPIRADO,
]

VALID_TRANSITIONS = {
    (LostReportStatus.ATIVO, LostReportStatus.ENCERRADO),
    (LostReportStatus.ATIVO, LostReportStatus.EXPIRADO),
}


@pytest.mark.parametrize("current", ALL_STATUSES)
@pytest.mark.parametrize("target", ALL_STATUSES)
def test_state_transition_matrix(current: LostReportStatus, target: LostReportStatus):
    expected = (current, target) in VALID_TRANSITIONS
    assert can_transition(current, target) is expected

    if expected:
        ensure_transition(current, target)
    else:
        with pytest.raises(InvalidTransition):
            ensure_transition(current, target)


# --- §8 / RN33: expiração em 60 dias de calendário ---


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        pytest.param(
            datetime(2026, 3, 1, 23, 59, tzinfo=UTC),
            False,
            id="day-59-end-of-day",
        ),
        pytest.param(
            datetime(2026, 3, 2, 0, 1, tzinfo=UTC),
            True,
            id="day-60-just-after-midnight",
        ),
        pytest.param(
            datetime(2026, 3, 3, 14, 30, tzinfo=UTC),
            True,
            id="day-61",
        ),
    ],
)
def test_is_expired_boundaries(now: datetime, expected: bool):
    created_at = datetime(2026, 1, 1, 14, 30, tzinfo=UTC)
    assert is_expired(created_at, now) is expected


def test_is_expired_false_on_creation_day():
    created_at = datetime(2026, 1, 1, 14, 30, tzinfo=UTC)
    assert is_expired(created_at, created_at + timedelta(hours=5)) is False


# --- §11: permissões por papel ---


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (Role.USUARIO, True),
        (Role.ATENDENTE, False),
        (Role.ADMIN, False),
    ],
)
def test_create_and_list_permissions_by_role(role: Role, expected: bool):
    actor = FakeActor(id=1, role=role)
    assert can_create_lost_report(actor) is expected
    assert can_list_lost_reports(actor) is expected


@pytest.mark.parametrize(
    ("actor_id", "role", "owner_id", "expected"),
    [
        (1, Role.USUARIO, 1, True),
        (2, Role.USUARIO, 1, False),
        (2, Role.ATENDENTE, 1, False),
        (2, Role.ADMIN, 1, False),
    ],
)
def test_access_lost_report_permission(actor_id: int, role: Role, owner_id: int, expected: bool):
    actor = FakeActor(id=actor_id, role=role)
    assert can_access_lost_report(actor, owner_id) is expected
