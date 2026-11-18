# scope section 5 (docs/diagrama.md): item lifecycle, RN01
from datetime import UTC, datetime
from itertools import product

import pytest

from domain.errors import InvalidTransition
from domain.items import ItemStatus, accepts_claims, transition
from models import Item

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)

ALLOWED = [
    (ItemStatus.REGISTERED, ItemStatus.AVAILABLE),  # received at the collection point
    (ItemStatus.REGISTERED, ItemStatus.CANCELLED),  # cancelled before reaching a point
    (ItemStatus.AVAILABLE, ItemStatus.IN_TRANSFER),  # sent to another point
    (ItemStatus.AVAILABLE, ItemStatus.RESERVED),  # a claim was approved
    (ItemStatus.AVAILABLE, ItemStatus.EXPIRED),  # 60 days without an owner
    (ItemStatus.IN_TRANSFER, ItemStatus.AVAILABLE),  # arrived at the new point
    (ItemStatus.RESERVED, ItemStatus.AVAILABLE),  # pickup deadline passed
    (ItemStatus.RESERVED, ItemStatus.RETURNED),  # owner picked it up
    (ItemStatus.EXPIRED, ItemStatus.DISPOSED),  # donated or discarded
]
NOT_ALLOWED = [pair for pair in product(ItemStatus, repeat=2) if pair not in ALLOWED]


@pytest.mark.parametrize(("current", "target"), ALLOWED)
def test_allowed_transition_returns_the_new_status(current, target):
    assert transition(current, target) == target


@pytest.mark.parametrize(("current", "target"), NOT_ALLOWED)
def test_any_other_transition_raises(current, target):
    with pytest.raises(InvalidTransition):
        transition(current, target)


def test_transition_to_changes_the_status():
    # in memory, no database; plain text, the way the status comes from the database
    item = Item(status="registrado")

    item.transition_to(ItemStatus.AVAILABLE, by=1, at=NOW)

    assert item.status == ItemStatus.AVAILABLE


def test_transition_to_outside_the_diagram_keeps_the_status():
    item = Item(status=ItemStatus.RETURNED)

    # the example in scope section 15: a returned item never goes back
    with pytest.raises(InvalidTransition):
        item.transition_to(ItemStatus.AVAILABLE, by=1, at=NOW)

    assert item.status == ItemStatus.RETURNED


@pytest.mark.parametrize(
    ("status", "accepts"),
    [
        (ItemStatus.REGISTERED, False),
        (ItemStatus.AVAILABLE, True),
        (ItemStatus.IN_TRANSFER, True),
        (ItemStatus.RESERVED, False),
        (ItemStatus.RETURNED, False),
        (ItemStatus.EXPIRED, False),
        (ItemStatus.DISPOSED, False),
        (ItemStatus.CANCELLED, False),
    ],
)
def test_only_items_on_a_shelf_or_on_their_way_accept_claims(status, accepts):
    # the "Aceita nova reivindicação" column of the table in scope section 5
    assert accepts_claims(status) is accepts
