from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from models.lost_report import LostReport
from models.notification import Notification
from repositories.base import Repository


class NotificationRepository(Repository[Notification]):
    model = Notification

    def exists(self, lost_report_id: int, item_id: int) -> bool:
        stmt = select(Notification.id).where(
            Notification.lost_report_id == lost_report_id,
            Notification.item_id == item_id,
        )
        return self._session.scalar(stmt) is not None

    def create_if_not_exists(self, lost_report_id: int, item_id: int) -> None:
        stmt = (
            insert(Notification)
            .values(
                lost_report_id=lost_report_id,
                item_id=item_id,
            )
            .on_conflict_do_nothing(index_elements=["lost_report_id", "item_id"])
        )
        self._session.execute(stmt)

    def list_by_user(self, user_id: int) -> Sequence[Notification]:
        stmt = (
            select(Notification)
            .join(
                LostReport,
                Notification.lost_report_id == LostReport.id,
            )
            .where(LostReport.user_id == user_id)
            .order_by(
                Notification.created_at.desc(),
                Notification.id.desc(),
            )
        )
        return self._session.scalars(stmt).all()

    def get_by_user(self, notification_id: int, user_id: int) -> Notification | None:
        stmt = (
            select(Notification)
            .join(
                LostReport,
                Notification.lost_report_id == LostReport.id,
            )
            .where(
                Notification.id == notification_id,
                LostReport.user_id == user_id,
            )
            .with_for_update(of=Notification)
        )
        return self._session.scalar(stmt)
