from fastapi import APIRouter, Response, status

from app.deps import CurrentUser, NowDep, SessionDep
from app.schemas.notification import MarkRead, NotificationList, UnreadCount
from app.services import notification_service

# Доступны и пользователю с незаполненным профилем: колокольчик есть и у черновика
router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(user: CurrentUser, session: SessionDep) -> NotificationList:
    return notification_service.list_notifications(session, user)


@router.get("/unread-count")
def unread_count(user: CurrentUser, session: SessionDep) -> UnreadCount:
    return UnreadCount(unread_count=notification_service.unread_count(session, user))


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(body: MarkRead, user: CurrentUser, session: SessionDep, now: NowDep) -> Response:
    notification_service.mark_read(session, now, user, body.up_to)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
