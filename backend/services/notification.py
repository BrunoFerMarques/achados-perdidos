from collections.abc import Sequence

from domain.clock import Clock
from domain.errors import NotificationNotFound
from domain.permissions import (
    can_access_notification,
    can_list_notifications,
    ensure,
)
from models import User
from models.notification import Notification
from repositories.unit_of_work import UnitOfWork


class NotificationService:
    def __init__(self, uow: UnitOfWork, clock: Clock):
        self._uow = uow
        self._clock = clock

    def list_mine(self, actor: User) -> Sequence[Notification]:
        ensure(can_list_notifications(actor))
        return self._uow.notifications.list_by_user(actor.id)

    def mark_as_read(self, actor: User, notification_id: int) -> Notification:
        ensure(can_list_notifications(actor))

        notification = self._uow.notifications.get_by_user(notification_id, actor.id)

        if notification is None:
            raise NotificationNotFound()

        report = self._uow.lost_reports.get(notification.lost_report_id)

        if report is None or not can_access_notification(actor, report.user_id):
            raise NotificationNotFound()

        # Reading twice must preserve the original timestamp.
        if notification.read_at is None:
            notification.read_at = self._clock.now()

        self._uow.commit()
        return notification
