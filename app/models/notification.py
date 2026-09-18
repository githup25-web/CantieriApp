from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from beanie import Document
from pydantic import ConfigDict, Field


class Notification(Document):
    id: UUID = Field(default_factory=uuid4)

    # Who should receive the notification
    recipient_user_id: UUID
    # Optional org scope (used to support "my notifications" via org membership)
    organization_id: UUID | None = None

    # Event type identifier (e.g. "preventivo.status_changed")
    type: str

    # The entity this notification refers to (preventivo_id, task_id, etc.)
    entity_id: UUID | str | None = None

    # Idempotency key used to avoid duplicates in multi-process/multi-dispatch scenarios.
    # Must be unique per logical event occurrence.
    #
    # Default value is provided to keep backward compatibility with existing
    # code/tests that may still create Notification without explicitly setting it.
    idempotency_key: str = Field(default_factory=lambda: str(uuid4()))

    # Free-form event metadata
    payload: dict[str, Any] = Field(default_factory=dict)

    is_read: bool = False

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "notifications"
        # MongoDB indexes used by Beanie (format compatibile con beanie 1.x)
        # Nota: l'unicità va garantita tramite gestione upsert/duplicate a runtime
        # oppure con un meccanismo di index-unique compatibile con la tua versione di Beanie.
        indexes = [
            [("recipient_user_id", 1), ("is_read", 1), ("created_at", -1)],
            [("organization_id", 1), ("created_at", -1)],
            [("type", 1), ("created_at", -1)],
            [("idempotency_key", 1)],
        ]

    model_config = ConfigDict(populate_by_name=True)
