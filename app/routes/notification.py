from __future__ import annotations

from uuid import UUID

from beanie.operators import In
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.membership import Membership
from app.models.notification import Notification
from app.models.user import User

router = APIRouter(prefix="/notification", tags=["notification"])


class NotificationReadResponse(BaseModel):
    id: str
    is_read: bool


@router.get("/my", response_model=list[dict])
async def get_my_notifications(current_user: User = Depends(get_current_user)) -> list[dict]:
    # Two queries to stay compatible with Beanie operator support:
    # 1) notifications explicitly addressed to the user
    # 2) notifications scoped to any org the user belongs to
    memberships = await Membership.find(Membership.user_id == current_user.id).to_list()
    organization_ids = [m.organization_id for m in memberships]

    recipient_notifications = await Notification.find(
        Notification.recipient_user_id == current_user.id
    ).to_list()

    org_notifications: list[Notification] = []
    if organization_ids:
        org_notifications = await Notification.find(
            In(Notification.organization_id, organization_ids)
        ).to_list()

    # Union (dedupe by notification id)
    by_id: dict[UUID, Notification] = {n.id: n for n in recipient_notifications}
    for n in org_notifications:
        by_id[n.id] = n

    notifications = sorted(by_id.values(), key=lambda n: n.created_at, reverse=True)

    return [
        {
            "id": str(n.id),
            "type": n.type,
            "entity_id": str(n.entity_id) if n.entity_id is not None else None,
            "organization_id": str(n.organization_id) if n.organization_id is not None else None,
            "payload": n.payload,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]


@router.post("/{id}/read", response_model=NotificationReadResponse)
async def mark_notification_read(
    id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
) -> NotificationReadResponse:
    try:
        notification = await Notification.get(id)
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Notification load failed: {exc}")

    # Only the recipient is allowed to mark a notification as read.
    # Membership/organization scope must NOT grant access for POST /{id}/read.
    if notification.recipient_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    notification.is_read = True
    await notification.save()

    return NotificationReadResponse(id=str(notification.id), is_read=notification.is_read)
