# scope §11 (docs/diagrama.md): who may see, edit and delete user accounts
from dataclasses import dataclass

import pytest

from domain.errors import PermissionDenied
from domain.permissions import (
    can_change_role,
    can_list_users,
    can_manage_collection_points,
    can_manage_user,
    ensure,
)
from domain.roles import Role

OWN_ID = 1
OTHER_ID = 2


@dataclass
class FakeActor:
    """Stands in for the logged-in User: the rules only read id and role."""

    id: int
    role: str


@pytest.mark.parametrize(
    ("role", "allowed"),
    [(Role.USUARIO, False), (Role.ATENDENTE, False), (Role.ADMIN, True)],
)
def test_only_admin_lists_users(role, allowed):
    assert can_list_users(FakeActor(OWN_ID, role)) is allowed


@pytest.mark.parametrize(
    ("role", "target_id", "allowed"),
    [
        (Role.USUARIO, OWN_ID, True),
        (Role.USUARIO, OTHER_ID, False),
        (Role.ATENDENTE, OWN_ID, True),
        (Role.ATENDENTE, OTHER_ID, False),
        (Role.ADMIN, OWN_ID, True),
        (Role.ADMIN, OTHER_ID, True),
    ],
)
def test_user_manages_own_account_and_admin_manages_any(role, target_id, allowed):
    assert can_manage_user(FakeActor(OWN_ID, role), target_id) is allowed


@pytest.mark.parametrize(
    ("role", "target_id", "allowed"),
    [
        (Role.USUARIO, OWN_ID, False),
        (Role.USUARIO, OTHER_ID, False),
        (Role.ATENDENTE, OTHER_ID, False),
        (Role.ADMIN, OTHER_ID, True),
        (Role.ADMIN, OWN_ID, False),
    ],
)
def test_only_admin_changes_role_and_never_their_own(role, target_id, allowed):
    assert can_change_role(FakeActor(OWN_ID, role), target_id) is allowed


@pytest.mark.parametrize(
    ("role", "allowed"),
    [(Role.USUARIO, False), (Role.ATENDENTE, False), (Role.ADMIN, True)],
)
def test_only_admin_manages_collection_points(role, allowed):
    # RN40
    assert can_manage_collection_points(FakeActor(OWN_ID, role)) is allowed


def test_ensure_raises_permission_denied_when_not_allowed():
    with pytest.raises(PermissionDenied):
        ensure(False)


def test_ensure_lets_an_allowed_operation_through():
    ensure(True)
