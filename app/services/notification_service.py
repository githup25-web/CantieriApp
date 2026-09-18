from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from app.core.events import dispatcher
from app.core.events_contract import OFFICIAL_EVENT_NAMES
from app.core.firebase_push import send_firebase_push
from app.models.membership import Membership
from app.models.notification import Notification
from app.models.user import User


def _dedupe_preserve_order(items: list[UUID]) -> list[UUID]:
    seen: set[UUID] = set()
    out: list[UUID] = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _build_idempotency_key(
    *,
    event_name: str,
    recipient_user_id: UUID,
    entity_id: UUID | str | None,
    event_instance_id: str | None,
) -> str:
    # Deterministic anti-duplication key.
    # event_instance_id should be provided by producers when possible to represent
    # a specific occurrence of the event (best); otherwise we fall back to payload-derived values.
    ent = str(entity_id) if entity_id is not None else "none"
    inst = event_instance_id or "unknown"
    return f"{event_name}|r={recipient_user_id}|e={ent}|i={inst}"


async def create_notification_for_event(
    *,
    event_name: str,
    payload: dict[str, Any],
) -> None:
    """
    Generic listener: context must provide:
    - organization_id: UUID | None
    - recipient_user_id: UUID | None
    - entity_id: UUID | str | None
    - data: dict (optional)
    """
    organization_id = payload.get("organization_id")
    recipient_user_id = payload.get("recipient_user_id")
    entity_id = payload.get("entity_id")
    data = payload.get("data", {})
    event_instance_id = payload.get("event_instance_id")

    data_dict: dict[str, Any] = data if isinstance(data, dict) else {}

    recipients: list[UUID] = []
    if isinstance(recipient_user_id, UUID):
        recipients.append(recipient_user_id)

    # Org scope: create for all users in that organization
    if isinstance(organization_id, UUID):
        memberships = await Membership.find(Membership.organization_id == organization_id).to_list()
        recipients.extend([m.user_id for m in memberships])

    recipients = _dedupe_preserve_order(recipients)

    if not recipients:
        return

    created_notifications: list[Notification] = []

    # Insert one-by-one to allow per-recipient idempotency handling (and push only on true inserts).
    # Multi-process safety is ensured by Mongo unique index on Notification.idempotency_key.
    for rid in recipients:
        idem_key = _build_idempotency_key(
            event_name=event_name,
            recipient_user_id=rid,
            entity_id=entity_id,
            event_instance_id=event_instance_id,
        )

        notif = Notification(
            recipient_user_id=rid,
            organization_id=organization_id,
            type=event_name,
            entity_id=entity_id,
            idempotency_key=idem_key,
            payload=data_dict,
            is_read=False,
        )

        try:
            await notif.insert()
            created_notifications.append(notif)
        except Exception:
            # Duplicate (or other race) => ignore (idempotent).
            continue

    # Best-effort push: schedule only for notifications that were actually inserted.
    for notif in created_notifications:
        user = await User.find_one(User.id == notif.recipient_user_id)
        device_token = getattr(user, "device_token", None)
        if device_token:
            asyncio.create_task(
                send_firebase_push(
                    device_token=device_token,
                    title="Notifica",
                    body=event_name,
                    data={"notification_id": str(notif.id), "idempotency_key": notif.idempotency_key},
                )
            )


async def register_notification_listeners() -> None:
    """
    Backward-compatible async entrypoint used by main.py startup.
    Kept deterministic (no reliance on FastAPI startup side-effects beyond calling this).
    """
    _register_notification_listeners_sync()


def _register_notification_listeners_sync() -> None:
    # Register mapping: for each official domain event, we reuse generic creator.
    # This keeps dispatcher/notification_service aligned with PASSO 16 contracts.
    event_names = sorted(OFFICIAL_EVENT_NAMES)

    # Prevent duplicate registration (main.py startup + module import)
    already = getattr(_register_notification_listeners_sync, "_registered", False)
    if already:
        return
    setattr(_register_notification_listeners_sync, "_registered", True)

    for name in event_names:
        async def _listener(ctx: dict[str, Any], _name: str = name) -> None:
            await create_notification_for_event(event_name=_name, payload=ctx)

        dispatcher.register(name, _listener)


# Ensure dispatcher has notification listeners even in scripts/tests that
# don't run FastAPI startup events.
_register_notification_listeners_sync()
