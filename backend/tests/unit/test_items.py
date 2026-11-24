# scope section 5 (docs/diagrama.md): item lifecycle, RN01; what the public listing shows, RN52
from datetime import UTC, datetime
from itertools import product

import pytest

from domain.custody import CustodyEvent
from domain.errors import InvalidTransition
from domain.items import (
    DOCUMENT_TEXT,
    DOCUMENTS_CATEGORY,
    ItemStatus,
    accepts_claims,
    public_text,
    transition,
)
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
    # RN06: a change that didn't happen leaves no line in the history
    assert item.history == []


def test_rn06_transition_to_writes_one_line_at_the_items_point():
    item = Item(status=ItemStatus.AVAILABLE, collection_point_id=7)

    item.transition_to(ItemStatus.RESERVED, by=3, at=NOW)

    [record] = item.history
    assert (record.event, record.collection_point_id, record.actor_id, record.at) == (
        CustodyEvent.RESERVATION,
        7,
        3,
        NOW,
    )


def test_rn02_receive_moves_the_item_to_the_counters_point_before_the_line():
    # the finder chose point 7, but the object was handed in at point 9
    item = Item(status=ItemStatus.REGISTERED, collection_point_id=7)

    item.receive(9, by=3, at=NOW)

    assert item.status == ItemStatus.AVAILABLE
    assert item.collection_point_id == 9
    assert [(r.event, r.collection_point_id) for r in item.history] == [(CustodyEvent.RECEIPT, 9)]


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
    # coluna "Aceita nova reivindicação" da tabela de status do item no escopo
    assert accepts_claims(status) is accepts


# RN52: a document's description has personal data; the listing shows a fixed text instead
def test_rn52_a_document_shows_only_the_fixed_text():
    assert public_text(DOCUMENTS_CATEGORY, "RG de João Silva") == DOCUMENT_TEXT


def test_any_other_category_shows_its_own_description():
    # the other way out of the if: without this test, a rule hiding every description would pass
    assert public_text("Garrafas e copos", "Garrafa azul") == "Garrafa azul"
