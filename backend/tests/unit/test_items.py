# scope section 5 (docs/diagrama.md): item lifecycle, RN01
from itertools import product

import pytest

from domain.errors import InvalidTransition
from domain.items import ItemStatus, transition
from models import Item

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

    item.transition_to(ItemStatus.AVAILABLE)

    assert item.status == ItemStatus.AVAILABLE


def test_transition_to_outside_the_diagram_keeps_the_status():
    item = Item(status=ItemStatus.RETURNED)

    # the example in scope section 15: a returned item never goes back
    with pytest.raises(InvalidTransition):
        item.transition_to(ItemStatus.AVAILABLE)

    assert item.status == ItemStatus.RETURNED
