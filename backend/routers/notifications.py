from fastapi import APIRouter

from dependencies import CurrentUserDep, NotificationServiceDep
from schemas.notification import NotificationOut

router = APIRouter(
    prefix="/v1/notifications",
    tags=["notifications"],
)


@router.get("", response_model=list[NotificationOut])
def list_my_notifications(
    current_user: CurrentUserDep,
    notifications: NotificationServiceDep,
):
    return notifications.list_mine(current_user)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationOut,
)
def mark_notification_as_read(
    notification_id: int,
    current_user: CurrentUserDep,
    notifications: NotificationServiceDep,
):
    return notifications.mark_as_read(current_user, notification_id)
