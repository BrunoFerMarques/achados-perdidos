# RN05: the item's way between collection points, in the model and in the database
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from domain.custody import CustodyEvent
from domain.errors import (
    InvalidTransition,
    ItemAlreadyAtThisPoint,
    ItemNotAvailable,
    ItemNotInTransfer,
)
from domain.items import ItemStatus
from models import Category, CollectionPoint, Color, Item, ItemQuestion, Location, User
from repositories.unit_of_work import UnitOfWork

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


@pytest.fixture
def uow(db):
    return UnitOfWork(db)


@pytest.fixture
def ana(db):
    """The attendant who moves the items."""
    user = User(name="Ana Lima", email="ana@example.com", password_hash="hash")
    db.add(user)
    db.flush()
    return user


def new_point(db, name: str) -> CollectionPoint:
    point = CollectionPoint(name=name)
    db.add(point)
    db.flush()
    return point


@pytest.fixture
def origin(db):
    return new_point(db, "Biblioteca")


@pytest.fixture
def destination(db):
    return new_point(db, "Restaurante")


def first_id(db, model) -> int:
    # categories, locations and colors are seeded by the migrations
    return db.scalar(select(model.id).order_by(model.id).limit(1))


@pytest.fixture
def new_item(db, origin):
    """new_item(status="disponivel", point=origin) -> Item, straight into that status."""

    def new_item(status: ItemStatus = ItemStatus.AVAILABLE, point=None) -> Item:
        item = Item(
            category_id=first_id(db, Category),
            location_id=first_id(db, Location),
            color_id=first_id(db, Color),
            collection_point_id=(point or origin).id,
            description="Garrafa azul com adesivo",
            found_date=date(2026, 11, 14),
            status=status,
            questions=[
                ItemQuestion(position=1, question="Cor?", answer="Azul"),
                ItemQuestion(position=2, question="Adesivo?", answer="Banda Queen"),
            ],
        )
        db.add(item)
        db.flush()
        return item

    return new_item


@pytest.fixture
def item(new_item):
    return new_item()


def put_in(item: Item, status: ItemStatus, destination: CollectionPoint) -> None:
    # straight to the status; on its way the item carries a destination, as the database requires
    item.status = status
    if status == ItemStatus.IN_TRANSFER:
        item.transfer_to_id = destination.id


# --- the model ---


def test_rn06_sending_and_arriving_write_one_line_at_each_end(db, item, ana, origin, destination):
    item.transfer_to(destination.id, by=ana.id, at=NOW)
    db.flush()
    assert (item.status, item.collection_point_id, item.transfer_to_id) == (
        ItemStatus.IN_TRANSFER,
        origin.id,
        destination.id,
    )

    item.arrive(by=ana.id, at=NOW + timedelta(hours=2))
    db.flush()

    assert (item.status, item.collection_point_id, item.transfer_to_id) == (
        ItemStatus.AVAILABLE,
        destination.id,
        None,
    )
    assert [(r.event, r.collection_point_id, r.at) for r in item.history] == [
        (CustodyEvent.TRANSFER_OUT, origin.id, NOW),
        (CustodyEvent.TRANSFER_IN, destination.id, NOW + timedelta(hours=2)),
    ]


@pytest.mark.parametrize(
    "status", [ItemStatus.REGISTERED, ItemStatus.IN_TRANSFER, ItemStatus.RESERVED]
)
def test_rn05_only_an_item_on_the_shelf_is_sent(new_item, ana, destination, status):
    item = new_item()
    put_in(item, status, destination)

    with pytest.raises(ItemNotAvailable):
        item.transfer_to(destination.id, by=ana.id, at=NOW)
    assert item.history == []


def test_item_is_not_sent_to_the_point_it_is_at(item, ana, origin):
    with pytest.raises(ItemAlreadyAtThisPoint):
        item.transfer_to(origin.id, by=ana.id, at=NOW)
    assert (item.status, item.transfer_to_id) == (ItemStatus.AVAILABLE, None)


def test_item_not_on_its_way_does_not_arrive(item, ana, origin):
    with pytest.raises(ItemNotInTransfer):
        item.arrive(by=ana.id, at=NOW)
    assert item.collection_point_id == origin.id


@pytest.mark.parametrize("status", [ItemStatus.RESERVED, ItemStatus.IN_TRANSFER])
def test_rn02_only_a_registered_item_is_received(new_item, ana, destination, status):
    # the diagram's arrows RESERVADO -> DISPONIVEL and EM_TRANSFERENCIA -> DISPONIVEL belong to
    # the claim and to arrive(), not to a receipt at any counter
    item = new_item()
    put_in(item, status, destination)

    with pytest.raises(InvalidTransition):
        item.receive(destination.id, by=ana.id, at=NOW)
    assert item.history == []


# --- items_transfer_to_id_check ---


def test_destination_only_while_in_transfer(db, item, destination):
    item.transfer_to_id = destination.id

    with pytest.raises(IntegrityError, match="items_transfer_to_id_check"):
        db.flush()
    db.rollback()


def test_item_in_transfer_always_has_a_destination(db, item):
    item.status = ItemStatus.IN_TRANSFER

    with pytest.raises(IntegrityError, match="items_transfer_to_id_check"):
        db.flush()
    db.rollback()


def test_destination_is_never_the_point_it_left(db, item, origin):
    item.status = ItemStatus.IN_TRANSFER
    item.transfer_to_id = origin.id

    with pytest.raises(IntegrityError, match="items_transfer_to_id_check"):
        db.flush()
    db.rollback()


# --- the item's row lock: a transfer, an arrival, a receipt and an approval take turns ---


def test_item_get_for_update_selects_the_row_for_update(uow, item, sent_sql):
    uow.items.get_for_update(item.id)

    assert sent_sql[-1].rstrip().endswith("FOR UPDATE")


def test_rn05_item_get_for_update_reloads_a_row_changed_by_another_transaction(db, uow, item):
    # a transfer that waited for an approval must see "reservado", not the shelf it read
    # (RN05: a reserved item is not sent)
    # read from the database before the change below; a plain SELECT would keep this stale copy
    db.refresh(item)
    assert item.status == ItemStatus.AVAILABLE
    db.execute(text("UPDATE items SET status = 'reservado' WHERE id = :id"), {"id": item.id})

    locked = uow.items.get_for_update(item.id)

    assert locked is item
    assert locked.status == ItemStatus.RESERVED


# --- the list of items on their way ---


def test_list_in_transfer_keeps_the_items_leaving_or_heading_to_the_points(
    db, uow, new_item, ana, origin, destination
):
    third = new_point(db, "Ginásio")
    leaving = new_item()
    leaving.transfer_to(destination.id, by=ana.id, at=NOW)
    arriving = new_item(point=third)
    arriving.transfer_to(origin.id, by=ana.id, at=NOW)
    elsewhere = new_item(point=third)
    elsewhere.transfer_to(destination.id, by=ana.id, at=NOW)
    new_item()  # on the shelf at the origin: not on its way
    db.flush()

    assert [i.id for i in uow.items.list_in_transfer({origin.id})] == [leaving.id, arriving.id]
    assert [i.id for i in uow.items.list_in_transfer(None)] == [
        leaving.id,
        arriving.id,
        elsewhere.id,
    ]
    assert uow.items.list_in_transfer(set()) == []
