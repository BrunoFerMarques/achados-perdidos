# quem pode ver, editar e excluir contas
from dataclasses import dataclass

import pytest

from domain.errors import PermissionDenied
from domain.permissions import (
    can_cancel_claim,
    can_change_role,
    can_claim,
    can_list_users,
    can_manage_collection_points,
    can_manage_user,
    can_operate_item,
    can_review_claim,
    can_review_claims,
    can_transfer_items,
    can_unblock_user,
    can_view_custody,
    ensure,
)
from domain.roles import Role

OWN_ID = 1
OTHER_ID = 2


@dataclass
class FakeActor:
    """Faz o papel do User logado: as regras só leem id e role."""

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
def test_only_admin_unblocks_users(role, allowed):
    assert can_unblock_user(FakeActor(OWN_ID, role)) is allowed


@pytest.mark.parametrize(
    ("role", "allowed"),
    [(Role.USUARIO, False), (Role.ATENDENTE, False), (Role.ADMIN, True)],
)
def test_only_admin_manages_collection_points(role, allowed):
    # RN40
    assert can_manage_collection_points(FakeActor(OWN_ID, role)) is allowed


@pytest.mark.parametrize(
    ("role", "allowed"),
    [(Role.USUARIO, True), (Role.ATENDENTE, False), (Role.ADMIN, False)],
)
def test_only_users_claim_items(role, allowed):
    # atendente e admin analisam reivindicações, não fazem
    assert can_claim(FakeActor(OWN_ID, role)) is allowed


@pytest.mark.parametrize(("claimant_id", "allowed"), [(OWN_ID, True), (OTHER_ID, False)])
def test_only_the_claimant_cancels_a_claim(claimant_id, allowed):
    assert can_cancel_claim(FakeActor(OWN_ID, Role.USUARIO), claimant_id) is allowed


@pytest.mark.parametrize(
    ("role", "allowed"),
    [(Role.USUARIO, False), (Role.ATENDENTE, True), (Role.ADMIN, True)],
)
def test_attendants_and_admins_review_claims(role, allowed):
    assert can_review_claims(FakeActor(OWN_ID, role)) is allowed


POINT_ID = 10
OTHER_POINT_ID = 20


@pytest.mark.parametrize(
    ("role", "actor_point_ids", "allowed"),
    [
        (Role.ATENDENTE, {POINT_ID}, True),
        (Role.ATENDENTE, {OTHER_POINT_ID, POINT_ID}, True),
        (Role.ATENDENTE, {OTHER_POINT_ID}, False),
        (Role.ATENDENTE, set(), False),
        (Role.ADMIN, set(), True),
        # usuário não se vincula a ponto; se o papel mudou depois, só o vínculo não basta
        (Role.USUARIO, {POINT_ID}, False),
    ],
)
def test_rn41_attendant_operates_only_items_at_their_points(role, actor_point_ids, allowed):
    assert can_operate_item(FakeActor(OWN_ID, role), POINT_ID, actor_point_ids) is allowed


@pytest.mark.parametrize(
    ("role", "claimant_id", "actor_point_ids", "allowed"),
    [
        (Role.ATENDENTE, OTHER_ID, {POINT_ID}, True),
        (Role.ATENDENTE, OTHER_ID, {OTHER_POINT_ID}, False),
        # reivindicou como usuário e depois virou atendente: continua sem julgar a própria
        (Role.ATENDENTE, OWN_ID, {POINT_ID}, False),
        (Role.ADMIN, OTHER_ID, set(), True),
        (Role.ADMIN, OWN_ID, set(), False),
        (Role.USUARIO, OTHER_ID, {POINT_ID}, False),
    ],
)
def test_review_needs_the_items_point_and_someone_elses_claim(
    role, claimant_id, actor_point_ids, allowed
):
    actor = FakeActor(OWN_ID, role)

    assert can_review_claim(actor, claimant_id, POINT_ID, actor_point_ids) is allowed


@pytest.mark.parametrize(
    ("role", "allowed"),
    [(Role.USUARIO, False), (Role.ATENDENTE, True), (Role.ADMIN, True)],
)
def test_rn53_only_staff_see_the_custody_history(role, allowed):
    assert can_view_custody(FakeActor(OWN_ID, role)) is allowed


@pytest.mark.parametrize(
    ("role", "allowed"),
    [(Role.USUARIO, False), (Role.ATENDENTE, True), (Role.ADMIN, True)],
)
def test_rn05_only_staff_transfer_items(role, allowed):
    assert can_transfer_items(FakeActor(OWN_ID, role)) is allowed


def test_ensure_raises_permission_denied_when_not_allowed():
    with pytest.raises(PermissionDenied):
        ensure(False)


def test_ensure_lets_an_allowed_operation_through():
    ensure(True)
