from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from models import Item
from models.lost_report import LostReport
from models.notification import Notification


def test_rn31_same_pair_creates_only_one_notification(uow, new_user, new_report, new_item):
    user = new_user("alice@example.com")
    report = new_report(user)
    item = new_item()

    uow.notifications.create_if_not_exists(report.id, item.id)
    uow.flush()

    uow.notifications.create_if_not_exists(report.id, item.id)
    uow.flush()
    uow.commit()

    notifications = uow.notifications.list_by_user(user.id)

    assert len(notifications) == 1
    assert notifications[0].lost_report_id == report.id
    assert notifications[0].item_id == item.id


def test_rn31_database_rejects_duplicate_notification(db, uow, new_user, new_report, new_item):
    user = new_user("alice@example.com")
    report = new_report(user)
    item = new_item()

    uow.notifications.create_if_not_exists(report.id, item.id)
    uow.commit()

    db.add(
        Notification(
            lost_report_id=report.id,
            item_id=item.id,
        )
    )

    with pytest.raises(
        IntegrityError,
        match="notifications_lost_report_id_item_id_key",
    ):
        db.flush()

    db.rollback()


def test_list_by_user_returns_only_owner_notifications_newest_first(
    db, uow, new_user, new_report, new_item
):
    alice = new_user("alice@example.com")
    bob = new_user("bob@example.com")

    alice_report = new_report(alice)
    bob_report = new_report(bob)

    first = new_item()
    second = new_item()
    third = new_item()

    uow.notifications.create_if_not_exists(alice_report.id, first.id)
    uow.notifications.create_if_not_exists(alice_report.id, second.id)
    uow.notifications.create_if_not_exists(alice_report.id, third.id)
    uow.notifications.create_if_not_exists(bob_report.id, first.id)

    older = datetime(2026, 11, 20, tzinfo=UTC)
    newer = datetime(2026, 11, 21, tzinfo=UTC)

    # IDs alone must not determine chronological order.
    db.execute(
        update(Notification).where(Notification.item_id == first.id).values(created_at=newer)
    )
    db.execute(
        update(Notification)
        .where(Notification.item_id.in_([second.id, third.id]))
        .values(created_at=older)
    )
    uow.commit()

    notifications = uow.notifications.list_by_user(alice.id)

    assert [n.item_id for n in notifications] == [
        first.id,
        third.id,
        second.id,
    ]

    assert all(n.lost_report_id == alice_report.id for n in notifications)

    assert len(uow.notifications.list_by_user(bob.id)) == 1


def test_user_without_notifications_gets_empty_list(uow, new_user):
    user = new_user("alice@example.com")

    assert uow.notifications.list_by_user(user.id) == []


@pytest.mark.parametrize("target", ["report", "item"])
def test_database_cascades_notification_deletion(db, uow, new_user, new_report, new_item, target):
    user = new_user("alice@example.com")
    report = new_report(user)
    item = new_item()

    uow.notifications.create_if_not_exists(report.id, item.id)
    uow.commit()

    notification_id = uow.notifications.list_by_user(user.id)[0].id

    # SQL deletion to verify database cascade, not ORM cascade.
    if target == "report":
        db.execute(delete(LostReport).where(LostReport.id == report.id))
    else:
        db.execute(delete(Item).where(Item.id == item.id))

    uow.commit()
    db.expire_all()

    saved = db.scalar(select(Notification).where(Notification.id == notification_id))

    assert saved is None


def test_notification_starts_unread(uow, new_user, new_report, new_item):
    user = new_user("alice@example.com")
    report = new_report(user)
    item = new_item()

    uow.notifications.create_if_not_exists(report.id, item.id)
    uow.commit()

    notification = uow.notifications.list_by_user(user.id)[0]

    assert notification.created_at is not None
    assert notification.read_at is None
